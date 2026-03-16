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
    'bootstrap_servers': ['kafka-frames:9092'],  # Fixed: use container name
    'auto_offset_reset': 'earliest',
    'consumer_timeout_ms': 30000,
    'group_id': 'frame_analyzer_working_group',  # New group ID
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore')),
    'enable_auto_commit': True,
    'auto_commit_interval_ms': 1000
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
            logger.info(f"📡 Connecting to Kafka with config: {KAFKA_CONFIG['bootstrap_servers']}")
            consumer = KafkaConsumer(KAFKA_TOPIC, **KAFKA_CONFIG)
            logger.info(f"📡 Subscribed to Kafka topic: {KAFKA_TOPIC}")

            # Manual partition assignment to avoid coordinator issues
            from kafka import TopicPartition
            partition = TopicPartition(KAFKA_TOPIC, 0)
            consumer.assign([partition])
            consumer.seek_to_beginning(partition)
            
            logger.info("🔍 Seeking to beginning and processing messages...")
            
            message_count = 0
            session_messages = 0
            
            for message in consumer:
                message_count += 1
                
                try:
                    message_data = message.value
                    msg_session_id = message_data.get('session_id')
                    
                    if msg_session_id == self.session_id:
                        session_messages += 1
                        logger.info(f"📄 Found message {session_messages} for session {self.session_id}")
                        self._process_frame_message(message_data)
                    
                    # Log progress
                    if message_count % 100 == 0:
                        logger.info(f"📊 Processed {message_count} messages, found {session_messages} for our session")
                    
                    # Safety limit
                    if message_count > 1000:
                        logger.info("Reached message limit, stopping")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error processing message {message_count}: {e}")
                    continue

            consumer.close()
            logger.info(f"✅ Kafka processing complete. Total messages: {message_count}, Session messages: {session_messages}")
            
        except Exception as e:
            logger.error(f"❌ Failed to consume from Kafka: {e}")

    def _process_frame_message(self, message_dict):
        try:
            # Check if it's a frame message
            if message_dict.get('type') != 'frame':
                logger.debug(f"Skipping non-frame message: {message_dict.get('type')}")
                return

            inner_data_obj = message_dict.get('frame_data', {})
            frame_b64 = inner_data_obj.get('frame_data')

            if not frame_b64 or not isinstance(frame_b64, str):
                logger.warning("No valid frame data found in message")
                return

            # Skip very small frames (test frames)
            if len(frame_b64) < 1000:
                logger.debug("Skipping small test frame")
                return

            # Decode and process frame
            frame_bytes = base64.b64decode(frame_b64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

            if frame is None:
                logger.warning("Could not decode frame")
                return

            if self.analyzer:
                logger.info(f"🔍 Analyzing frame {self.frames_processed_count + 1}...")
                self.analyzer.analyze_frame_professional(frame, self.session_id)
                self.frames_processed_count += 1
                
                if self.frames_processed_count % 10 == 0:
                    logger.info(f"📊 Analyzed {self.frames_processed_count} frames...")
                    
        except Exception as e:
            logger.error(f"❌ Error during frame processing: {e}")

    def _finalize_analysis(self):
        if not self.analyzer:
            logger.error("No analyzer available")
            return False
            
        try:
            logger.info("📊 Generating comprehensive session analysis report...")
            session_report = self.analyzer.get_comprehensive_session_analysis(self.session_id)
            
            output_path = f"/app/analysis_results_{self.interview_id}.json"
            with open(output_path, 'w') as f:
                json.dump(session_report, f, indent=4)

            logger.info(f"✅ Analysis complete. Report saved to {output_path}")
            logger.info(f"📈 Total Frames Analyzed: {self.frames_processed_count}")
            
            # Show summary
            if 'analysis_summary' in session_report:
                summary = session_report['analysis_summary']
                logger.info(f"🎯 Integrity Score: {summary.get('professional_integrity_score', 'N/A')}")
                logger.info(f"📝 Assessment: {summary.get('overall_assessment', 'N/A')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate final report: {e}")
            return False

# --- Script Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Session Analyzer with Fixed Kafka.")
    parser.add_argument('--session_id', required=True, help='The unique session ID for the interview.')
    parser.add_argument('--interview_id', required=True, type=int, help='The corresponding interview ID.')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode.')

    args = parser.parse_args()
    
    if args.auto_process:
        logger.info(f"🚀 Starting analysis for session: {args.session_id}, interview: {args.interview_id}")
        processor = EnhancedFrameProcessor(session_id=args.session_id, interview_id=args.interview_id)
        
        if processor.process_frames():
            logger.info("🎉 Analysis completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Analysis failed!")
            sys.exit(1)
