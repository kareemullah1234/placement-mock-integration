import argparse
import json
import os
import sys
import logging
import time
import base64
import cv2
import numpy as np
import mysql.connector
from kafka import KafkaConsumer

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'mysql8-container',
    'database': 'mock_interview_platform',
    'user': 'root',
    'password': 'demopass',
    'port': '3306'
}

KAFKA_TOPIC = 'interview-frames'
KAFKA_CONFIG = {
    'bootstrap_servers': ['kafka-frames:9092'],
    'auto_offset_reset': 'earliest',
    'consumer_timeout_ms': 20000,
    'group_id': 'frame_analyzer_final_test', # Using a new group_id to ensure a fresh start
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore'))
}

# --- Main Processor Class ---
class EnhancedFrameProcessor:
    def __init__(self, session_id, interview_id):
        self.session_id = session_id
        self.interview_id = interview_id
        self.frames_processed_count = 0
        self.analyzer = None
        try:
            from advanced_video_analysis_api import analyzer as professional_analyzer
            self.analyzer = professional_analyzer
            logger.info("✅ Successfully loaded ProfessionalFrameAnalyzer.")
        except Exception as e:
            logger.error(f"❌ Error loading ProfessionalFrameAnalyzer: {e}")

    def process_frames(self):
        logger.info(f"🎥 Starting frame processing from Kafka for session: {self.session_id}")
        self._consume_from_kafka()
        return self._finalize_analysis()

    def _consume_from_kafka(self):
        try:
            consumer = KafkaConsumer(KAFKA_TOPIC, **KAFKA_CONFIG)
            logger.info(f"📡 Subscribed to Kafka topic: {KAFKA_TOPIC}")

            # --- KEY FIX ---
            # Poll the consumer to ensure it's assigned partitions BEFORE seeking.
            # This line forces the client to sync with the Kafka broker and get its assignment.
            consumer.poll(timeout_ms=1000)

            # Now that partitions are assigned, we can safely seek to the beginning.
            logger.info("Seeking to the beginning of the topic to read all messages.")
            consumer.seek_to_beginning()

            for message in consumer:
                if message.value.get('session_id') == self.session_id:
                    self._process_frame_message(message.value)
                else:
                    # This log helps confirm we are reading messages, even if they aren't for our session
                    logger.debug(f"Skipping message with session_id: {message.value.get('session_id')}")

            consumer.close()
        except Exception as e:
            logger.error(f"❌ Failed to consume from Kafka: {e}")

    def _process_frame_message(self, message_dict):
        try:
            inner_data_obj = message_dict.get('frame_data', {})
            frame_b64 = inner_data_obj.get('frame_data')

            if not frame_b64 or not isinstance(frame_b64, str):
                return

            frame_bytes = base64.b64decode(frame_b64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

            if frame is None:
                return
            
            if self.analyzer:
                self.analyzer.analyze_frame_professional(frame, self.session_id)
                self.frames_processed_count += 1
                if self.frames_processed_count % 50 == 0:
                    logger.info(f"📊 Analyzed {self.frames_processed_count} frames...")
        except Exception as e:
            logger.error(f"❌ Error during single frame processing: {e}")

    def _finalize_analysis(self):
        if not self.analyzer:
            return False
        try:
            logger.info("Generating comprehensive session analysis report...")
            session_report = self.analyzer.get_comprehensive_session_analysis(self.session_id)
            output_path = f"/app/analysis_results_{self.interview_id}.json"
            with open(output_path, 'w') as f:
                json.dump(session_report, f, indent=4)
            
            logger.info(f"✅ Analysis complete. Report saved to {output_path}")
            print(f"Total Frames Analyzed: {self.frames_processed_count}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to generate final report: {e}")
            return False

# --- Script Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Session Analyzer.")
    parser.add_argument('--session_id', required=True, help='The unique session ID for the interview.')
    parser.add_argument('--interview_id', required=True, type=int, help='The corresponding interview ID.')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode.')
    
    args = parser.parse_args()
    if args.auto_process:
        processor = EnhancedFrameProcessor(session_id=args.session_id, interview_id=args.interview_id)
        if processor.process_frames():
            sys.exit(0)
        else:
            sys.exit(1)
