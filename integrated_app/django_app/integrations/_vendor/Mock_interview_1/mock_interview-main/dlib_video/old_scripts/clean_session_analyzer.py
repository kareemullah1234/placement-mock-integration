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
import shutil
import tempfile

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
    'consumer_timeout_ms': 60000,  # 60 seconds timeout
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore'))
}

# --- Main Processor Class ---
class EnhancedFrameProcessor:
    def __init__(self, session_id, interview_id):
        self.session_id = session_id
        self.interview_id = interview_id
        
        # ADDED: Extract user_id from session_id for collision-safe filenames
        self.user_id = self._extract_user_id_from_session(session_id)
        
        self.frames_processed_count = 0
        self.session_frames = []
        self.temp_frames_dir = None
        self.analyzer = None
        
        try:
            from advanced_video_analysis_api import ProfessionalFrameAnalyzer
            self.analyzer = ProfessionalFrameAnalyzer()
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
        
        # Step 1: Scan Kafka for frames
        self._scan_kafka_for_frames()
        
        # Step 2: Process collected frames
        if self.session_frames:
            logger.info(f"🎬 Processing {len(self.session_frames)} stored frame messages")
            self._process_collected_frames()
        else:
            logger.warning("⚠️ No frames found for this session")
            
        # Step 3: Generate final report
        return self._finalize_analysis()

    def _scan_kafka_for_frames(self):
        """Enhanced Kafka scanning with better consumer group management"""
        try:
            # Use unique consumer group for each session
            consumer_group = f"enhanced_analyzer_{self.session_id}_{int(time.time())}"
            
            kafka_config = KAFKA_CONFIG.copy()
            kafka_config['group_id'] = consumer_group
            
            logger.info(f"📡 Starting enhanced Kafka scan for session: {self.session_id}")
            
            consumer = KafkaConsumer(KAFKA_TOPIC, **kafka_config)
            
            # Get partition assignment
            partitions = consumer.assignment()
            if not partitions:
                consumer.poll(timeout_ms=1000)
                partitions = consumer.assignment()
            
            logger.info(f"📡 Consumer created, scanning partition 0 from beginning...")
            
            # Seek to beginning for comprehensive scan
            consumer.seek_to_beginning()
            
            messages_scanned = 0
            session_messages = 0
            frames_found = 0
            
            start_time = time.time()
            
            for message in consumer:
                messages_scanned += 1
                
                try:
                    if message.value.get('session_id') == self.session_id:
                        session_messages += 1
                        
                        # Check if this is a frame message
                        if 'frame_data' in message.value:
                            frames_found += 1
                            self.session_frames.append(message.value)
                            logger.info(f"🎬 Found frame {frames_found} for session {self.session_id}")
                    
                    # Progress logging
                    if messages_scanned % 100 == 0:
                        logger.info(f"📊 Scanned {messages_scanned} messages, session messages: {session_messages}, frames found: {frames_found}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    continue
                    
                # Timeout check
                if time.time() - start_time > 60:  # 60 second timeout
                    logger.info("⏰ Kafka scan timeout reached")
                    break
            
            scan_duration = time.time() - start_time
            logger.info(f"✅ Kafka scan completed in {scan_duration:.2f}s")
            logger.info(f"📊 Total messages scanned: {messages_scanned}")
            logger.info(f"🎯 Session messages found: {session_messages}")
            logger.info(f"🎬 Frame messages found: {frames_found}")
            
            consumer.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to scan Kafka: {e}")

    def _process_collected_frames(self):
        """Process all collected frames with professional analysis"""
        if not self.analyzer:
            logger.error("❌ No analyzer available for frame processing")
            return
            
        self.temp_frames_dir = tempfile.mkdtemp(prefix="session_frames_")
        
        for i, frame_message in enumerate(self.session_frames, 1):
            try:
                self._process_single_frame(frame_message, i)
                
                # Progress updates
                if i % 5 == 0 or i == len(self.session_frames):
                    logger.info(f"📈 Progress: {i}/{len(self.session_frames)} frames processed")
                    
            except Exception as e:
                logger.error(f"❌ Error processing frame {i}: {e}")
                continue

    def _process_single_frame(self, frame_message, frame_number):
        """Process a single frame with enhanced analysis"""
        try:
            inner_data_obj = frame_message.get('frame_data', {})
            frame_b64 = inner_data_obj.get('frame_data')
            
            if not frame_b64 or not isinstance(frame_b64, str):
                return
                
            # Decode frame
            frame_bytes = base64.b64decode(frame_b64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
            
            if frame is None:
                return
                
            # Professional analysis
            analysis_result = self.analyzer.analyze_frame_professional(frame, self.session_id)
            
            # Count faces for logging
            face_count = 0
            if hasattr(analysis_result, 'get') and 'face_analysis' in analysis_result:
                face_count = len(analysis_result.get('face_analysis', {}).get('faces', []))
            
            logger.info(f"✅ Frame analyzed: {face_count} faces detected")
            self.frames_processed_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error during single frame processing: {e}")

    def _finalize_analysis(self):
        """Generate comprehensive analysis report with collision-safe filename"""
        if not self.analyzer:
            logger.error("❌ No analyzer available for final report generation")
            return False
            
        try:
            # Clean up temporary directory
            if self.temp_frames_dir and os.path.exists(self.temp_frames_dir):
                shutil.rmtree(self.temp_frames_dir)
                logger.info("🧹 Cleaned up temporary frames directory")
            
            logger.info(f"📊 Generating enhanced analysis report for session: {self.session_id}")
            
            # Get comprehensive session analysis
            session_report = self.analyzer.get_comprehensive_session_analysis(self.session_id)
            
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
                    'frames_found': len(self.session_frames),
                    'analysis_type': 'enhanced_professional',
                    'filename': output_filename
                },
                'analysis': session_report
            }
            
            with open(output_path, 'w') as f:
                json.dump(enhanced_report, f, indent=4)
            
            logger.info("✅ Comprehensive session analysis completed")
            logger.info(f"✅ Enhanced analysis report saved to: {output_path}")
            logger.info(f"📈 Processing Summary:")
            logger.info(f"   • Messages scanned: {getattr(self, 'messages_scanned', 'N/A')}")
            logger.info(f"   • Session messages: {getattr(self, 'session_messages', len(self.session_frames))}")
            logger.info(f"   • Frames found: {len(self.session_frames)}")
            logger.info(f"   • Frames processed: {self.frames_processed_count}")
            logger.info(f"🎯 SUCCESS: Enhanced processing completed with {self.frames_processed_count} frames")
            logger.info(f"📁 Collision-safe filename: {output_filename}")
            logger.info(f"📊 User: {self.user_id}, Interview: {self.interview_id}, Session: {self.session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate enhanced final report: {e}")
            return False

# --- Script Entry Point ---
if __name__ == "__main__":
    logger.info("🚀 Starting Enhanced Video Frame Analysis")
    
    parser = argparse.ArgumentParser(description="Enhanced Session Analyzer with Professional Frame Analysis and Collision-Safe Filenames")
    parser.add_argument('--session_id', required=True, help='The unique session ID for the interview.')
    parser.add_argument('--interview_id', required=True, type=int, help='The corresponding interview ID.')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated processing mode.')
    
    args = parser.parse_args()
    
    logger.info(f"   Session ID: {args.session_id}")
    logger.info(f"   Interview ID: {args.interview_id}")
    
    if args.auto_process:
        try:
            processor = EnhancedFrameProcessor(session_id=args.session_id, interview_id=args.interview_id)
            success = processor.process_frames()
            
            if success:
                logger.info("🎉 Enhanced video analysis completed successfully!")
                logger.info(f"📊 Final Stats: {processor.frames_processed_count} frames processed from {len(processor.session_frames)} found")
                sys.exit(0)
            else:
                logger.error("❌ Enhanced video analysis failed!")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"❌ Critical error in enhanced analysis: {e}")
            sys.exit(1)
    else:
        logger.info("ℹ️ Use --auto_process flag to run the analysis")
        sys.exit(0)
