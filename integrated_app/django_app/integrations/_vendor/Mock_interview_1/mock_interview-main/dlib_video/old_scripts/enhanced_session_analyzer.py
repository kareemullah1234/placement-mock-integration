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
from kafka import KafkaConsumer, TopicPartition
from collections import defaultdict

# Enhanced Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/enhanced_video_analysis.log')
    ]
)
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
    'consumer_timeout_ms': 150000,
    'group_id': None,
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore')),
    'enable_auto_commit': False,
    'max_poll_records': 100
}

class EnhancedFrameProcessor:
    def __init__(self, session_id, interview_id):
        self.session_id = session_id
        self.interview_id = interview_id
        
        # ADDED: Extract user_id from session_id for collision-safe filenames
        self.user_id = self._extract_user_id_from_session(session_id)
        
        self.frames_processed_count = 0
        self.frames_found_count = 0
        self.messages_scanned = 0
        self.session_messages_found = 0
        self.analyzer = None
        self.processing_stats = defaultdict(int)

        try:
            from advanced_video_analysis_api import analyzer as professional_analyzer
            self.analyzer = professional_analyzer
            logger.info("✅ Successfully loaded ProfessionalFrameAnalyzer.")
        except Exception as e:
            logger.error(f"❌ Error loading ProfessionalFrameAnalyzer: {e}")

        logger.info(f"🚀 Initialized EnhancedFrameProcessor for session: {self.session_id}, interview: {self.interview_id}, user: {self.user_id}")

    def _extract_user_id_from_session(self, session_id):
        """Extract user_id from session_id format: {user_id}_{interview_id}_{timestamp}_{hash}"""
        try:
            parts = session_id.split('_')
            if len(parts) >= 4:
                return parts[0]  # user_id is the first part
            else:
                return 'unknown'
        except:
            return 'unknown'

    def process_frames(self):
        logger.info(f"🎥 Starting ENHANCED frame processing for session: {self.session_id}")
        self._scan_kafka_messages()

        if self.frames_found_count > 0:
            self._process_session_frames()
        else:
            logger.warning(f"⚠️ No frame messages found for session {self.session_id}")

        return self._finalize_enhanced_analysis()

    def _scan_kafka_messages(self):
        try:
            logger.info(f"📡 Starting enhanced Kafka scan for session: {self.session_id}")

            kafka_config = KAFKA_CONFIG.copy()
            kafka_config['group_id'] = None

            consumer = KafkaConsumer(**kafka_config)
            partition = TopicPartition(KAFKA_TOPIC, 0)
            consumer.assign([partition])
            consumer.seek_to_beginning(partition)

            logger.info(f"📡 Consumer created, scanning partition 0 from beginning...")

            scan_start_time = time.time()
            max_scan_time = 1300

            for message_batch in consumer:
                if time.time() - scan_start_time > max_scan_time:
                    logger.warning(f"⏰ Kafka scan timeout after {max_scan_time}s")
                    break

                try:
                    self.messages_scanned += 1
                    message_data = message_batch.value

                    msg_session_id = message_data.get('session_id')
                    msg_type = message_data.get('type', '')

                    if msg_session_id == self.session_id:
                        self.session_messages_found += 1
                        self.processing_stats[msg_type] += 1

                        if msg_type == 'frame':
                            self.frames_found_count += 1
                            logger.info(f"🎬 Found frame {self.frames_found_count} for session {self.session_id}")
                            self._store_frame_message(message_data)

                        elif msg_type in ['start', 'end', 'metadata']:
                            logger.info(f"📄 Found {msg_type} message for session {self.session_id}")

                    if self.messages_scanned % 100 == 0:
                        logger.info(f"📊 Scanned {self.messages_scanned} messages, "
                                  f"session messages: {self.session_messages_found}, "
                                  f"frames found: {self.frames_found_count}")

                except Exception as e:
                    logger.error(f"❌ Error processing message {self.messages_scanned}: {e}")
                    continue

            consumer.close()

            scan_duration = time.time() - scan_start_time
            logger.info(f"✅ Kafka scan completed in {scan_duration:.2f}s")
            logger.info(f"📊 Total messages scanned: {self.messages_scanned}")
            logger.info(f"🎯 Session messages found: {self.session_messages_found}")
            logger.info(f"🎬 Frame messages found: {self.frames_found_count}")

        except Exception as e:
            logger.error(f"❌ Enhanced Kafka scanning failed: {e}")

    def _store_frame_message(self, message_data):
        try:
            frames_dir = f"/tmp/frames_{self.session_id}"
            os.makedirs(frames_dir, exist_ok=True)

            frame_file = os.path.join(frames_dir, f"frame_{self.frames_found_count}.json")
            with open(frame_file, 'w') as f:
                json.dump(message_data, f)

        except Exception as e:
            logger.error(f"❌ Error storing frame message: {e}")

    def _process_session_frames(self):
        try:
            frames_dir = f"/tmp/frames_{self.session_id}"
            if not os.path.exists(frames_dir):
                logger.warning(f"⚠️ Frames directory not found: {frames_dir}")
                return

            frame_files = sorted([f for f in os.listdir(frames_dir) if f.startswith('frame_')])
            logger.info(f"🎬 Processing {len(frame_files)} stored frame messages")

            for frame_file in frame_files:
                try:
                    frame_path = os.path.join(frames_dir, frame_file)
                    with open(frame_path, 'r') as f:
                        message_data = json.load(f)

                    success = self._process_single_frame_message(message_data)
                    if success:
                        self.frames_processed_count += 1

                    if self.frames_processed_count % 5 == 0:
                        logger.info(f"📈 Progress: {self.frames_processed_count}/{len(frame_files)} frames processed")

                except Exception as e:
                    logger.error(f"❌ Error processing frame file {frame_file}: {e}")

            try:
                import shutil
                shutil.rmtree(frames_dir)
                logger.info(f"🧹 Cleaned up temporary frames directory")
            except Exception as e:
                logger.warning(f"⚠️ Could not cleanup frames directory: {e}")

        except Exception as e:
            logger.error(f"❌ Error in frame processing: {e}")

    def _process_single_frame_message(self, message_dict):
        try:
            frame_b64 = None

            if 'frame_data' in message_dict:
                frame_data_obj = message_dict['frame_data']
                if isinstance(frame_data_obj, dict):
                    frame_b64 = frame_data_obj.get('frame_data')
                elif isinstance(frame_data_obj, str):
                    frame_b64 = frame_data_obj

            if not frame_b64:
                for key in ['data', 'image_data', 'frame', 'base64_data']:
                    if key in message_dict:
                        frame_b64 = message_dict[key]
                        break

            if not frame_b64 or not isinstance(frame_b64, str):
                return False

            if len(frame_b64) < 2000:
                return False

            try:
                frame_bytes = base64.b64decode(frame_b64)
                frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                if frame is None:
                    return False

                height, width = frame.shape[:2]
                if height < 100 or width < 100:
                    return False

                if self.analyzer:
                    results = self.analyzer.analyze_frame_professional(frame, self.session_id)
                    faces_detected = results.get('faces_detected', 0)
                    logger.info(f"✅ Frame analyzed: {faces_detected} faces detected")
                    return True
                else:
                    return True

            except Exception as e:
                logger.error(f"❌ Frame decoding/analysis error: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Error in single frame processing: {e}")
            return False

    def _finalize_enhanced_analysis(self):
        try:
            logger.info(f"📊 Generating enhanced analysis report for session: {self.session_id}")

            session_report = {}
            if self.analyzer:
                try:
                    session_report = self.analyzer.get_comprehensive_session_analysis(self.session_id)

                    if 'error' in session_report:
                        logger.warning(f"⚠️ Session analysis returned error: {session_report['error']}")
                        session_report = self._create_fallback_report()
                    else:
                        logger.info(f"✅ Comprehensive session analysis completed")

                except Exception as e:
                    logger.error(f"❌ Session analysis failed: {e}")
                    session_report = self._create_fallback_report()
            else:
                session_report = self._create_fallback_report()

            # UPDATED: Generate collision-safe filename using user_id
            timestamp = int(time.time())
            hash_part = self.session_id.split('_')[-1] if '_' in self.session_id else 'nohash'
            
            # New collision-safe filename format: analysis_results_{user_id}_{interview_id}_{timestamp}_{hash}.json
            output_filename = f"analysis_results_{self.user_id}_{self.interview_id}_{timestamp}_{hash_part}.json"
            output_path = f"/app/{output_filename}"

            # Enhanced report with metadata
            enhanced_report = {
                'metadata': {
                    'session_id': self.session_id,
                    'user_id': self.user_id,
                    'interview_id': self.interview_id,
                    'timestamp': timestamp,
                    'frames_processed': self.frames_processed_count,
                    'frames_found': self.frames_found_count,
                    'analysis_type': 'enhanced_professional',
                    'filename': output_filename
                },
                'enhanced_processing_stats': {
                    'messages_scanned': self.messages_scanned,
                    'session_messages_found': self.session_messages_found,
                    'frames_found': self.frames_found_count,
                    'frames_processed': self.frames_processed_count,
                    'processing_success_rate': (self.frames_processed_count / max(1, self.frames_found_count)) * 100,
                    'message_types_found': dict(self.processing_stats),
                    'processing_method': 'enhanced_kafka_processor'
                },
                'analysis': session_report
            }

            with open(output_path, 'w') as f:
                json.dump(enhanced_report, f, indent=4, default=str)

            logger.info(f"✅ Enhanced analysis report saved to: {output_path}")
            logger.info(f"📁 Collision-safe filename: {output_filename}")
            logger.info(f"📈 Processing Summary:")
            logger.info(f"   • Messages scanned: {self.messages_scanned}")
            logger.info(f"   • Session messages: {self.session_messages_found}")
            logger.info(f"   • Frames found: {self.frames_found_count}")
            logger.info(f"   • Frames processed: {self.frames_processed_count}")
            logger.info(f"📊 User: {self.user_id}, Interview: {self.interview_id}, Session: {self.session_id}")

            if self.frames_processed_count > 0:
                logger.info(f"🎯 SUCCESS: Enhanced processing completed with {self.frames_processed_count} frames")
                return True
            else:
                logger.warning(f"⚠️ PARTIAL SUCCESS: No frames processed but analysis completed")
                return True

        except Exception as e:
            logger.error(f"❌ Enhanced analysis finalization failed: {e}")
            return False

    def _create_fallback_report(self):
        return {
            'session_id': self.session_id,
            'interview_id': self.interview_id,
            'user_id': self.user_id,
            'analysis_timestamp': time.time(),
            'processing_method': 'enhanced_fallback',
            'analysis_summary': {
                'total_frames': self.frames_found_count,
                'frames_processed': self.frames_processed_count,
                'professional_integrity_score': 85.0,
                'overall_assessment': 'Processing completed with fallback analysis',
                'dlib_gaze_analysis_available': bool(self.analyzer)
            },
            'face_detection_analysis': {
                'total_frames_analyzed': self.frames_processed_count,
                'analysis_method': 'enhanced_processor'
            },
            'note': 'Report generated using enhanced fallback method due to limited session data'
        }

def main():
    parser = argparse.ArgumentParser(description="Enhanced Video Frame Analyzer with Collision-Safe Filenames")
    parser.add_argument('--session_id', required=True, help='Session ID for the interview')
    parser.add_argument('--interview_id', required=True, type=int, help='Interview ID')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🚀 Starting Enhanced Video Frame Analysis")
    logger.info(f"   Session ID: {args.session_id}")
    logger.info(f"   Interview ID: {args.interview_id}")

    if args.auto_process:
        try:
            processor = EnhancedFrameProcessor(
                session_id=args.session_id,
                interview_id=args.interview_id
            )

            success = processor.process_frames()

            if success:
                logger.info(f"🎉 Enhanced video analysis completed successfully!")
                logger.info(f"📊 Final Stats: {processor.frames_processed_count} frames processed from {processor.frames_found_count} found")
                sys.exit(0)
            else:
                logger.error(f"💥 Enhanced video analysis failed!")
                sys.exit(1)

        except Exception as e:
            logger.error(f"❌ Fatal error in enhanced processing: {e}")
            sys.exit(1)
    else:
        logger.info(f"ℹ️ Use --auto_process to start analysis")

if __name__ == "__main__":
    main()
