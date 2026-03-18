#!/usr/bin/env python3
"""
Test script to find available sessions in Kafka and run frame analysis
"""

import json
import time
import logging
from kafka import KafkaConsumer, TopicPartition
from collections import defaultdict
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_TOPIC = 'interview-frames'
KAFKA_CONFIG = {
    'bootstrap_servers': ['kafka-frames:9092'],
    'auto_offset_reset': 'earliest',
    'consumer_timeout_ms': 30000,  # 30 seconds timeout for discovery
    'group_id': None,
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore')),
    'enable_auto_commit': False,
    'max_poll_records': 500
}

def discover_available_sessions():
    """Discover all available sessions in Kafka"""
    logger.info("🔍 Discovering available sessions in Kafka...")
    
    try:
        consumer = KafkaConsumer(**KAFKA_CONFIG)
        partition = TopicPartition(KAFKA_TOPIC, 0)
        consumer.assign([partition])
        consumer.seek_to_beginning(partition)
        
        session_stats = defaultdict(lambda: {
            'frame_count': 0,
            'start_messages': 0,
            'end_messages': 0,
            'metadata_messages': 0,
            'first_timestamp': None,
            'last_timestamp': None,
            'sample_message': None
        })
        
        total_messages = 0
        start_time = time.time()
        
        for message in consumer:
            # Stop after 30 seconds or if no more messages
            if time.time() - start_time > 30:
                logger.info("⏰ Discovery timeout reached")
                break
                
            try:
                total_messages += 1
                message_data = message.value
                
                session_id = message_data.get('session_id')
                msg_type = message_data.get('type', 'unknown')
                timestamp = message_data.get('timestamp', time.time())
                
                if session_id:
                    stats = session_stats[session_id]
                    
                    # Count message types
                    if msg_type == 'frame':
                        stats['frame_count'] += 1
                    elif msg_type == 'start':
                        stats['start_messages'] += 1
                    elif msg_type == 'end':
                        stats['end_messages'] += 1
                    elif msg_type == 'metadata':
                        stats['metadata_messages'] += 1
                    
                    # Track timestamps
                    if stats['first_timestamp'] is None:
                        stats['first_timestamp'] = timestamp
                    stats['last_timestamp'] = timestamp
                    
                    # Store a sample message
                    if stats['sample_message'] is None:
                        stats['sample_message'] = {
                            'type': msg_type,
                            'timestamp': timestamp,
                            'keys': list(message_data.keys())
                        }
                
                if total_messages % 100 == 0:
                    logger.info(f"📊 Scanned {total_messages} messages, found {len(session_stats)} sessions")
                    
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                continue
        
        consumer.close()
        
        logger.info(f"✅ Discovery completed!")
        logger.info(f"📊 Total messages scanned: {total_messages}")
        logger.info(f"🎯 Total sessions found: {len(session_stats)}")
        
        return dict(session_stats)
        
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        return {}

def display_sessions(session_stats):
    """Display available sessions in a nice format"""
    print("\n" + "="*80)
    print("🎬 AVAILABLE SESSIONS FOR FRAME ANALYSIS")
    print("="*80)
    
    if not session_stats:
        print("❌ No sessions found in Kafka")
        return []
    
    valid_sessions = []
    
    for i, (session_id, stats) in enumerate(session_stats.items(), 1):
        frame_count = stats['frame_count']
        
        print(f"\n{i:2d}. Session ID: {session_id}")
        print(f"    📹 Frame messages: {frame_count}")
        print(f"    🚀 Start messages: {stats['start_messages']}")
        print(f"    🏁 End messages: {stats['end_messages']}")
        print(f"    📄 Metadata messages: {stats['metadata_messages']}")
        
        if stats['first_timestamp'] and stats['last_timestamp']:
            duration = stats['last_timestamp'] - stats['first_timestamp']
            print(f"    ⏱️  Duration: {duration:.1f} seconds")
        
        print(f"    🔍 Sample message type: {stats['sample_message']['type'] if stats['sample_message'] else 'None'}")
        
        if frame_count > 0:
            print(f"    ✅ READY FOR ANALYSIS")
            valid_sessions.append((session_id, stats))
        else:
            print(f"    ⚠️  No frames available")
    
    print("\n" + "="*80)
    print(f"📊 Summary: {len(valid_sessions)} sessions with frames available for analysis")
    print("="*80)
    
    return valid_sessions

def extract_interview_id_from_session(session_id):
    """Extract interview ID from session ID"""
    try:
        # Try to extract from format: user_id_interview_id_timestamp_hash
        parts = session_id.split('_')
        if len(parts) >= 4:
            return int(parts[1])  # interview_id is usually the second part
        else:
            # Fallback: try to find numbers in session_id
            import re
            numbers = re.findall(r'\d+', session_id)
            if len(numbers) >= 2:
                return int(numbers[1])  # Take second number as interview_id
            elif numbers:
                return int(numbers[0])  # Take first number
            else:
                return 1  # Default fallback
    except:
        return 1  # Default fallback

def run_frame_analysis(session_id, interview_id):
    """Run the frame analysis for a specific session"""
    logger.info(f"🚀 Starting frame analysis for session: {session_id}")
    
    cmd = [
        'python', 'enhanced_session_analyzer.py',
        '--session_id', session_id,
        '--interview_id', str(interview_id),
        '--auto_process'
    ]
    
    try:
        logger.info(f"🔧 Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            logger.info(f"✅ Analysis completed successfully!")
            logger.info(f"📊 Output: {result.stdout}")
            return True, result.stdout
        else:
            logger.error(f"❌ Analysis failed with return code: {result.returncode}")
            logger.error(f"❌ Error output: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Analysis timed out after 5 minutes")
        return False, "Analysis timed out"
    except Exception as e:
        logger.error(f"❌ Failed to run analysis: {e}")
        return False, str(e)

def find_output_files(session_id, interview_id):
    """Find the output files generated by the analysis"""
    import glob
    import os
    
    # Look for the comprehensive analysis file
    pattern1 = f"/app/comprehensive_frame_analysis_*_{interview_id}_*.json"
    pattern2 = f"/app/comprehensive_frame_analysis_*.json"
    
    files = glob.glob(pattern1) + glob.glob(pattern2)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return files

def main():
    print("🎬 KAFKA FRAME ANALYSIS TESTER")
    print("="*50)
    
    # Step 1: Discover available sessions
    print("\n1️⃣ Discovering available sessions...")
    session_stats = discover_available_sessions()
    
    # Step 2: Display sessions
    valid_sessions = display_sessions(session_stats)
    
    if not valid_sessions:
        print("❌ No sessions with frames found. Exiting.")
        return
    
    # Step 3: Let user choose or auto-select
    print(f"\n2️⃣ Select session for analysis:")
    print("   Enter session number (1-{}) or 'all' for all sessions:".format(len(valid_sessions)))
    
    try:
        choice = input("Your choice: ").strip().lower()
        
        sessions_to_analyze = []
        
        if choice == 'all':
            sessions_to_analyze = valid_sessions
            print(f"🎯 Selected ALL {len(valid_sessions)} sessions for analysis")
        else:
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(valid_sessions):
                    sessions_to_analyze = [valid_sessions[choice_num - 1]]
                    print(f"🎯 Selected session {choice_num}: {valid_sessions[choice_num - 1][0]}")
                else:
                    print("❌ Invalid selection")
                    return
            except ValueError:
                print("❌ Invalid input")
                return
        
        # Step 4: Run analysis
        print(f"\n3️⃣ Running analysis on {len(sessions_to_analyze)} session(s)...")
        
        successful_analyses = []
        failed_analyses = []
        
        for session_id, stats in sessions_to_analyze:
            interview_id = extract_interview_id_from_session(session_id)
            
            print(f"\n📹 Analyzing session: {session_id}")
            print(f"   Interview ID: {interview_id}")
            print(f"   Frames available: {stats['frame_count']}")
            
            success, output = run_frame_analysis(session_id, interview_id)
            
            if success:
                successful_analyses.append((session_id, interview_id))
                
                # Find output files
                output_files = find_output_files(session_id, interview_id)
                if output_files:
                    print(f"📁 Output file: {output_files[0]}")
                    
                    # Show file size
                    import os
                    file_size = os.path.getsize(output_files[0]) / 1024 / 1024
                    print(f"📊 File size: {file_size:.2f} MB")
                    
                    # Show frame count in file
                    try:
                        with open(output_files[0], 'r') as f:
                            data = json.load(f)
                            frame_count = len(data.get('individual_frame_analyses', []))
                            print(f"🎬 Frames analyzed in file: {frame_count}")
                    except:
                        pass
                else:
                    print("⚠️ Output file not found")
            else:
                failed_analyses.append((session_id, output))
        
        # Step 5: Summary
        print(f"\n4️⃣ ANALYSIS SUMMARY")
        print("="*50)
        print(f"✅ Successful analyses: {len(successful_analyses)}")
        print(f"❌ Failed analyses: {len(failed_analyses)}")
        
        if successful_analyses:
            print(f"\n✅ SUCCESSFUL ANALYSES:")
            for session_id, interview_id in successful_analyses:
                output_files = find_output_files(session_id, interview_id)
                if output_files:
                    print(f"   📁 {session_id} → {output_files[0]}")
                else:
                    print(f"   📁 {session_id} → (file not found)")
        
        if failed_analyses:
            print(f"\n❌ FAILED ANALYSES:")
            for session_id, error in failed_analyses:
                print(f"   💥 {session_id} → {error[:100]}...")
        
        print(f"\n🎉 Analysis complete! Check the output files for comprehensive frame-by-frame data.")
        
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
