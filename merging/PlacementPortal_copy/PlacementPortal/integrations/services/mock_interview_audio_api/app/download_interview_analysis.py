#!/usr/bin/env python3
"""
Download and view interview analysis JSON from HDFS
For use in video_to_text container
"""

import requests
import json
import os
import argparse
from datetime import datetime

def download_interview_json(interview_id, user_id, attempt_number, output_dir="."):
    """
    Download interview analysis JSON from HDFS
    
    Args:
        interview_id: Interview ID
        user_id: User ID 
        attempt_number: Attempt number
        output_dir: Directory to save the file (default: current directory)
    """
    
    # Construct expected filename pattern based on your HDFS structure
    filename = f"sandeep_G_STU000001_attempt_{attempt_number}_interview_{interview_id}.json"
    hdfs_path = f"/interview_sessions/{filename}"
    
    # HDFS WebHDFS REST API endpoint
    namenode_host = "namenode"
    namenode_port = "9870"
    
    try:
        # Download the JSON file from HDFS
        file_url = f"http://{namenode_host}:{namenode_port}/webhdfs/v1{hdfs_path}?op=OPEN"
        
        print(f"Downloading from HDFS: {hdfs_path}")
        print(f"URL: {file_url}")
        
        response = requests.get(file_url, timeout=60)
        
        if response.status_code == 200:
            # Save to local file
            local_filename = f"interview_{interview_id}_analysis.json"
            output_path = os.path.join(output_dir, local_filename)
            
            with open(output_path, 'w') as f:
                # Parse and pretty-format the JSON
                json_data = response.json()
                json.dump(json_data, f, indent=2, default=str)
            
            print(f"✅ Successfully downloaded and saved to: {output_path}")
            
            # Display summary information
            display_summary(json_data)
            
            return output_path
            
        else:
            print(f"❌ Failed to download file: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def display_summary(json_data):
    """Display a summary of the analysis results"""
    
    print("\n" + "="*60)
    print("INTERVIEW ANALYSIS SUMMARY")
    print("="*60)
    
    # Metadata
    metadata = json_data.get('metadata', {})
    print(f"Session ID: {metadata.get('session_id', 'N/A')}")
    print(f"Interview ID: {metadata.get('interview_id', 'N/A')}")
    print(f"User ID: {metadata.get('user_id', 'N/A')}")
    print(f"Analysis Type: {metadata.get('analysis_type', 'N/A')}")
    
    # Processing stats
    stats = metadata.get('processing_stats', {})
    print(f"\nProcessing Statistics:")
    print(f"  Frames processed: {stats.get('frames_processed', 0)}")
    print(f"  Audio files processed: {stats.get('audio_files_processed', 0)}")
    
    # Video analysis
    video_analysis = json_data.get('video_analysis', {})
    if video_analysis.get('success'):
        video_summary = video_analysis.get('session_summary', {})
        print(f"\nVideo Analysis:")
        print(f"  Frames analyzed: {video_summary.get('total_frames_analyzed', 0)}")
        print(f"  Eye contact: {video_summary.get('eye_contact_percentage', 0)}%")
        print(f"  Focus: {video_summary.get('focus_percentage', 0)}%")
        print(f"  Dominant emotion: {video_summary.get('dominant_emotion', 'unknown')}")
    
    # Audio analysis
    audio_analysis = json_data.get('audio_analysis', {})
    if audio_analysis.get('success'):
        audio_summary = audio_analysis.get('audio_analysis', {}).get('session_summary', {})
        print(f"\nAudio Analysis:")
        print(f"  Overall clarity: {audio_summary.get('overall_clarity', 'unknown')}")
        print(f"  Overall pace: {audio_summary.get('overall_pace', 'unknown')}")
        print(f"  Speaking duration: {audio_summary.get('aggregated_metrics', {}).get('speaking_duration', 0)} seconds")
        print(f"  Total duration: {audio_summary.get('aggregated_metrics', {}).get('total_duration', 0)} seconds")
    
    # Integrated assessment
    assessment = json_data.get('integrated_assessment', {})
    print(f"\nIntegrated Assessment:")
    print(f"  Overall performance: {assessment.get('overall_performance', 'unknown')}")
    print(f"  Interview readiness: {assessment.get('interview_readiness', 'unknown')}")
    print(f"  Key strengths: {', '.join(assessment.get('key_strengths', []))}")
    print(f"  Improvement areas: {', '.join(assessment.get('improvement_areas', []))}")
    
    # Correlation
    correlation = json_data.get('cross_modal_correlation', {}).get('overall_correlation', {})
    print(f"\nCross-modal Correlation:")
    print(f"  Correlation level: {correlation.get('correlation_level', 'unknown')}")
    print(f"  Correlation score: {correlation.get('correlation_score', 0)}")
    
    print("="*60)

def list_available_files():
    """List available interview session files in HDFS"""
    
    namenode_host = "namenode"
    namenode_port = "9870"
    
    try:
        # List files in interview_sessions directory
        list_url = f"http://{namenode_host}:{namenode_port}/webhdfs/v1/interview_sessions?op=LISTSTATUS"
        
        print("Available interview session files in HDFS:")
        
        response = requests.get(list_url, timeout=30)
        if response.status_code == 200:
            files_data = response.json()
            files = files_data.get('FileStatuses', {}).get('FileStatus', [])
            
            json_files = [f for f in files if f['pathSuffix'].endswith('.json')]
            
            if json_files:
                print(f"\nFound {len(json_files)} JSON files:")
                for file_info in json_files:
                    filename = file_info['pathSuffix']
                    size = file_info['length']
                    modified = file_info['modificationTime']
                    modified_date = datetime.fromtimestamp(modified/1000).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  📄 {filename} ({size} bytes, modified: {modified_date})")
            else:
                print("No JSON files found in /interview_sessions/")
                
        else:
            print(f"Failed to list files: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error listing files: {e}")

def main():
    parser = argparse.ArgumentParser(description="Download interview analysis JSON from HDFS")
    parser.add_argument('--interview_id', type=int, default=39, help='Interview ID')
    parser.add_argument('--user_id', type=int, default=1, help='User ID')
    parser.add_argument('--attempt', type=int, default=17, help='Attempt number')
    parser.add_argument('--output_dir', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--list', action='store_true', help='List available files in HDFS')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_files()
    else:
        result = download_interview_json(
            interview_id=args.interview_id,
            user_id=args.user_id, 
            attempt_number=args.attempt,
            output_dir=args.output_dir
        )
        
        if result:
            print(f"\n💾 Analysis saved to: {result}")
            print(f"📊 You can now view the detailed analysis in the JSON file")

if __name__ == "__main__":
    main()
