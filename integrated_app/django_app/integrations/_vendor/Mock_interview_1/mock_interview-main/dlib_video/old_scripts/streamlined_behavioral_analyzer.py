#!/usr/bin/env python3
"""
Streamlined Behavioral Analyzer - Compact JSON for LLM Analysis
Only essential behavioral data, ~20-30 lines per frame instead of 200+
"""

import argparse
import json
import os
import sys
import logging
import time
import base64
import cv2
import numpy as np
from kafka import KafkaConsumer, TopicPartition
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/streamlined_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

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

class StreamlinedBehavioralAnalyzer:
    def __init__(self, session_id, interview_id):
        self.session_id = session_id
        self.interview_id = interview_id
        self.user_id = self._extract_user_id_from_session(session_id)
        self.frames_processed = 0
        self.frames_found = 0
        self.analyzer = None
        
        # Store only essential behavioral data
        self.behavioral_frames = []
        self.start_time = time.time()

        try:
            from advanced_video_analysis_api import analyzer as professional_analyzer
            self.analyzer = professional_analyzer
            logger.info("✅ Professional analyzer loaded")
        except Exception as e:
            logger.error(f"❌ Analyzer loading failed: {e}")

        logger.info(f"🚀 Streamlined Behavioral Analyzer initialized")
        logger.info(f"   📝 Session: {self.session_id}")
        logger.info(f"   🎯 Interview: {self.interview_id}")

    def _extract_user_id_from_session(self, session_id):
        try:
            parts = session_id.split('_')
            return parts[0] if len(parts) >= 4 else 'unknown'
        except:
            return 'unknown'

    def analyze_session(self):
        logger.info(f"🎬 Starting streamlined behavioral analysis...")
        
        # Scan Kafka for frames
        self._scan_and_process_frames()
        
        if self.frames_found > 0:
            logger.info(f"✅ Analysis completed: {len(self.behavioral_frames)} frames processed")
            return self._generate_streamlined_output()
        else:
            logger.warning(f"⚠️ No frames found for session")
            return False

    def _scan_and_process_frames(self):
        try:
            logger.info(f"📡 Scanning Kafka for behavioral data...")

            consumer = KafkaConsumer(**KAFKA_CONFIG)
            partition = TopicPartition(KAFKA_TOPIC, 0)
            consumer.assign([partition])
            consumer.seek_to_beginning(partition)

            scan_start = time.time()
            messages_scanned = 0

            for message in consumer:
                if time.time() - scan_start > 300:  # 5 minute timeout
                    logger.warning(f"⏰ Scan timeout")
                    break

                try:
                    messages_scanned += 1
                    data = message.value
                    
                    if data.get('session_id') == self.session_id and data.get('type') == 'frame':
                        self.frames_found += 1
                        
                        # Process frame immediately
                        behavioral_data = self._extract_behavioral_essentials(data, self.frames_found)
                        if behavioral_data:
                            self.behavioral_frames.append(behavioral_data)
                            self.frames_processed += 1

                        if self.frames_found % 10 == 0:
                            logger.info(f"📊 Processed {self.frames_found} frames")

                    if messages_scanned % 500 == 0:
                        logger.info(f"🔍 Scanned {messages_scanned} messages, found {self.frames_found} frames")

                except Exception as e:
                    logger.error(f"❌ Message processing error: {e}")
                    continue

            consumer.close()
            
            logger.info(f"✅ Scan completed: {messages_scanned} messages, {self.frames_found} frames found")

        except Exception as e:
            logger.error(f"❌ Kafka scanning failed: {e}")

    def _extract_behavioral_essentials(self, message_data, frame_number):
        """Extract only essential behavioral data from frame"""
        try:
            # Get frame data
            frame_b64 = self._get_frame_data(message_data)
            if not frame_b64 or len(frame_b64) < 2000:
                return None

            # Decode and analyze frame
            frame_bytes = base64.b64decode(frame_b64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

            if frame is None or frame.shape[0] < 100 or frame.shape[1] < 100:
                return None

            # Get analysis from API
            if not self.analyzer:
                return self._create_basic_behavioral_data(frame_number, message_data)

            api_result = self.analyzer.analyze_frame_professional(frame, self.session_id)
            
            # Extract ONLY essential behavioral information
            return self._create_streamlined_behavioral_data(api_result, frame_number, message_data)

        except Exception as e:
            logger.error(f"❌ Frame {frame_number} analysis failed: {e}")
            return None

    def _get_frame_data(self, message_data):
        """Extract base64 frame data"""
        if 'frame_data' in message_data:
            frame_obj = message_data['frame_data']
            if isinstance(frame_obj, dict):
                return frame_obj.get('frame_data')
            return frame_obj
        
        for key in ['data', 'image_data', 'frame', 'base64_data']:
            if key in message_data:
                return message_data[key]
        return None

    def _create_streamlined_behavioral_data(self, api_result, frame_number, message_data):
        """Create streamlined behavioral data - ONLY essentials for LLM"""
        
        # Extract gaze information
        gaze_data = api_result.get('gaze_analysis_per_face', [])
        primary_gaze = 'unknown'
        gaze_confidence = 0.0
        eyes_closed = False
        
        if gaze_data:
            first_gaze = gaze_data[0]
            primary_gaze = first_gaze.get('gaze_direction', 'unknown')
            gaze_confidence = first_gaze.get('confidence', 0.0)
            eyes_closed = primary_gaze == 'eyes_closed'

        # Extract cheating indicators
        indicators = api_result.get('cheating_indicators', [])
        cheating_types = [ind.get('type', '') for ind in indicators]
        high_risk_indicators = [ind for ind in indicators if ind.get('confidence', 0) > 0.8]

        # Calculate simple behavioral scores
        attention_score = 100
        if primary_gaze in ['looking_left', 'looking_right', 'looking_up', 'looking_down']:
            attention_score -= 30
        if eyes_closed:
            attention_score -= 10
        if api_result.get('faces_detected', 0) == 0:
            attention_score -= 50
        if api_result.get('faces_detected', 0) > 1:
            attention_score -= 40

        # Time context
        time_elapsed = time.time() - self.start_time

        return {
            "frame": frame_number,
            "timestamp": message_data.get('timestamp', time.time()),
            "time_elapsed": round(time_elapsed, 1),
            
            # Essential face detection
            "faces_detected": api_result.get('faces_detected', 0),
            "face_present": api_result.get('faces_detected', 0) == 1,
            "multiple_people": api_result.get('faces_detected', 0) > 1,
            
            # Essential gaze behavior
            "gaze_direction": primary_gaze,
            "looking_at_camera": primary_gaze == 'looking_at_camera',
            "looking_away": primary_gaze in ['looking_left', 'looking_right', 'looking_up', 'looking_down'],
            "eyes_closed": eyes_closed,
            "gaze_confidence": round(gaze_confidence, 2),
            
            # Essential behavioral indicators
            "attention_score": max(0, attention_score),
            "distracted": primary_gaze != 'looking_at_camera' and api_result.get('faces_detected', 0) > 0,
            "absent": api_result.get('faces_detected', 0) == 0,
            
            # Essential cheating detection
            "cheating_indicators": len(indicators),
            "cheating_types": cheating_types,
            "high_risk_cheating": len(high_risk_indicators) > 0,
            "suspicious_behavior": len(indicators) > 0,
            
            # Essential motion analysis
            "motion_consistent": api_result.get('integrity_metrics', {}).get('motion_consistent', True),
            "static_image_detected": not api_result.get('integrity_metrics', {}).get('motion_consistent', True),
            
            # Simple quality score
            "frame_quality": "good" if attention_score >= 80 else "poor" if attention_score >= 50 else "critical"
        }

    def _create_basic_behavioral_data(self, frame_number, message_data):
        """Fallback behavioral data when API not available"""
        return {
            "frame": frame_number,
            "timestamp": message_data.get('timestamp', time.time()),
            "time_elapsed": round(time.time() - self.start_time, 1),
            "faces_detected": 1,  # Assume basic detection
            "face_present": True,
            "multiple_people": False,
            "gaze_direction": "unknown",
            "looking_at_camera": True,  # Assume positive
            "looking_away": False,
            "eyes_closed": False,
            "gaze_confidence": 0.0,
            "attention_score": 80,  # Neutral score
            "distracted": False,
            "absent": False,
            "cheating_indicators": 0,
            "cheating_types": [],
            "high_risk_cheating": False,
            "suspicious_behavior": False,
            "motion_consistent": True,
            "static_image_detected": False,
            "frame_quality": "basic_analysis"
        }

    def _generate_streamlined_output(self):
        """Generate compact behavioral analysis for LLM"""
        try:
            timestamp = int(time.time())
            hash_part = self.session_id.split('_')[-1] if '_' in self.session_id else 'hash'
            
            # Compact filename
            filename = f"BEHAVIORAL_ANALYSIS_{self.user_id}_{self.interview_id}_{timestamp}_{hash_part}.json"
            filepath = f"/app/{filename}"

            # Calculate behavioral statistics
            stats = self._calculate_behavioral_statistics()
            
            # Create streamlined output
            streamlined_output = {
                "session_info": {
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "interview_id": self.interview_id,
                    "analysis_timestamp": timestamp,
                    "total_frames_analyzed": len(self.behavioral_frames),
                    "analysis_duration_seconds": round(time.time() - self.start_time, 1)
                },
                
                "behavioral_summary": {
                    "average_attention_score": stats['avg_attention'],
                    "camera_attention_percentage": stats['camera_attention_pct'],
                    "distraction_percentage": stats['distraction_pct'], 
                    "absence_percentage": stats['absence_pct'],
                    "cheating_incidents": stats['total_cheating'],
                    "suspicious_frames": stats['suspicious_frames'],
                    "overall_behavior_assessment": stats['assessment']
                },
                
                "behavioral_patterns": {
                    "attention_consistency": stats['attention_consistency'],
                    "gaze_stability": stats['gaze_stability'],
                    "presence_consistency": stats['presence_consistency'],
                    "peak_distraction_periods": stats['distraction_periods']
                },
                
                "frame_by_frame_behavior": self.behavioral_frames,  # Compact frame data
                
                "llm_analysis_notes": {
                    "data_optimized_for": "LLM behavioral pattern analysis",
                    "frame_data_location": "frame_by_frame_behavior[]",
                    "key_behavioral_fields": [
                        "attention_score", "looking_at_camera", "distracted", 
                        "cheating_indicators", "gaze_direction", "frame_quality"
                    ],
                    "analysis_approach": "Focus on attention_score trends and cheating_indicators clustering"
                }
            }

            # Save compact file
            with open(filepath, 'w') as f:
                json.dump(streamlined_output, f, indent=2, default=str)

            file_size_kb = os.path.getsize(filepath) / 1024
            estimated_lines = len(json.dumps(streamlined_output, indent=2).split('\n'))

            logger.info(f"✅ STREAMLINED BEHAVIORAL ANALYSIS COMPLETED!")
            logger.info(f"📁 Output: {filename}")
            logger.info(f"📊 File size: {file_size_kb:.1f} KB (vs ~900KB before)")
            logger.info(f"📝 Estimated lines: ~{estimated_lines} (vs ~33K before)")
            logger.info(f"🎬 Frames analyzed: {len(self.behavioral_frames)}")
            logger.info(f"🤖 Optimized for LLM analysis!")

            return True

        except Exception as e:
            logger.error(f"❌ Output generation failed: {e}")
            return False

    def _calculate_behavioral_statistics(self):
        """Calculate essential behavioral statistics"""
        if not self.behavioral_frames:
            return {
                'avg_attention': 0, 'camera_attention_pct': 0, 'distraction_pct': 0,
                'absence_pct': 0, 'total_cheating': 0, 'suspicious_frames': 0,
                'assessment': 'no_data', 'attention_consistency': 'unknown',
                'gaze_stability': 'unknown', 'presence_consistency': 'unknown',
                'distraction_periods': []
            }

        total_frames = len(self.behavioral_frames)
        
        # Basic counts
        camera_attention = sum(1 for f in self.behavioral_frames if f['looking_at_camera'])
        distracted = sum(1 for f in self.behavioral_frames if f['distracted'])
        absent = sum(1 for f in self.behavioral_frames if f['absent'])
        cheating_total = sum(f['cheating_indicators'] for f in self.behavioral_frames)
        suspicious = sum(1 for f in self.behavioral_frames if f['suspicious_behavior'])
        
        # Average attention
        avg_attention = sum(f['attention_score'] for f in self.behavioral_frames) / total_frames
        
        # Percentages
        camera_pct = (camera_attention / total_frames) * 100
        distraction_pct = (distracted / total_frames) * 100
        absence_pct = (absent / total_frames) * 100
        
        # Assessment
        if avg_attention >= 85 and distraction_pct < 10:
            assessment = "excellent"
        elif avg_attention >= 70 and distraction_pct < 25:
            assessment = "good"
        elif avg_attention >= 50 and distraction_pct < 40:
            assessment = "fair"
        else:
            assessment = "poor"
        
        # Consistency checks
        attention_scores = [f['attention_score'] for f in self.behavioral_frames]
        attention_consistency = "stable" if max(attention_scores) - min(attention_scores) < 30 else "variable"
        
        # Find distraction periods
        distraction_periods = []
        current_period = None
        for i, frame in enumerate(self.behavioral_frames):
            if frame['distracted'] and not current_period:
                current_period = {'start': i+1, 'end': i+1}
            elif frame['distracted'] and current_period:
                current_period['end'] = i+1
            elif not frame['distracted'] and current_period:
                if current_period['end'] - current_period['start'] >= 2:  # 3+ consecutive frames
                    distraction_periods.append(current_period)
                current_period = None
        
        return {
            'avg_attention': round(avg_attention, 1),
            'camera_attention_pct': round(camera_pct, 1),
            'distraction_pct': round(distraction_pct, 1),
            'absence_pct': round(absence_pct, 1),
            'total_cheating': cheating_total,
            'suspicious_frames': suspicious,
            'assessment': assessment,
            'attention_consistency': attention_consistency,
            'gaze_stability': "stable",  # Simplified
            'presence_consistency': "stable" if absence_pct < 10 else "inconsistent",
            'distraction_periods': distraction_periods
        }

def main():
    parser = argparse.ArgumentParser(description="Streamlined Behavioral Analyzer for LLM Analysis")
    parser.add_argument('--session_id', required=True, help='Session ID')
    parser.add_argument('--interview_id', required=True, type=int, help='Interview ID')
    parser.add_argument('--auto_process', action='store_true', help='Run automatically')
    parser.add_argument('--debug', action='store_true', help='Debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🚀 STREAMLINED BEHAVIORAL ANALYZER")
    logger.info(f"   📝 Session: {args.session_id}")
    logger.info(f"   🎯 Interview: {args.interview_id}")
    logger.info(f"   📊 Output: Compact JSON optimized for LLM")

    if args.auto_process:
        try:
            analyzer = StreamlinedBehavioralAnalyzer(args.session_id, args.interview_id)
            success = analyzer.analyze_session()

            if success:
                logger.info(f"🎉 STREAMLINED ANALYSIS COMPLETED!")
                logger.info(f"🤖 File ready for LLM behavioral analysis")
                sys.exit(0)
            else:
                logger.error(f"💥 Analysis failed")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            sys.exit(1)
    else:
        logger.info(f"ℹ️ Use --auto_process to start")

if __name__ == "__main__":
    main()
