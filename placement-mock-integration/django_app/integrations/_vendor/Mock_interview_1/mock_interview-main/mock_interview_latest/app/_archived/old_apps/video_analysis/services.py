import cv2
import numpy as np
import json
import whisper
import requests
from django.conf import settings
from interview_system.models import Interview, InterviewResponse, InterviewFrames
from utils.hdfs_client import HDFSClient
from .computer_vision import ComputerVisionAnalyzer
from .transcript_analyzer import TranscriptAnalyzer
from .models import AnalysisResult

class AnalysisService:
    def __init__(self):
        self.hdfs_client = HDFSClient()
        self.cv_analyzer = ComputerVisionAnalyzer()
        self.transcript_analyzer = TranscriptAnalyzer()
    
    def process_interview_analysis(self, interview_id):
        """Process complete interview analysis"""
        try:
            interview = Interview.objects.get(id=interview_id)
            
            # Process video frames for cheating detection
            cv_results = self.analyze_video_frames(interview)
            
            # Process audio responses for transcript and evaluation
            transcript_results = self.analyze_audio_responses(interview)
            
            # Calculate overall scores
            overall_score = self.calculate_overall_score(cv_results, transcript_results)
            
            # Update interview with results
            interview.overall_score = overall_score['total_score']
            interview.cheating_detected = cv_results['cheating_detected']
            interview.cheating_confidence = cv_results['cheating_confidence']
            interview.analysis_completed = True
            interview.save()
            
            # Create analysis result record
            analysis_result, created = AnalysisResult.objects.get_or_create(
                interview=interview,
                defaults={
                    'cv_score': cv_results.get('cv_score', 0),
                    'transcript_score': transcript_results.get('overall_transcript_quality', 0),
                    'final_score': overall_score['total_score'],
                    'grade': overall_score['grade'],
                    'analysis_details': {
                        'cv_analysis': cv_results,
                        'transcript_analysis': transcript_results,
                        'overall_score': overall_score
                    }
                }
            )
            
            return {
                'interview_id': str(interview_id),
                'status': 'completed',
                'results': analysis_result.analysis_details
            }
            
        except Exception as e:
            print(f"Error in interview analysis: {e}")
            return {'error': str(e)}
    
    def analyze_video_frames(self, interview):
        """Analyze video frames for cheating detection"""
        try:
            frames_obj = interview.frames
            frames_data = self.hdfs_client.load_frames(frames_obj.frames_file_path)
            
            results = self.cv_analyzer.analyze_frames(frames_data['frames'])
            
            # Update frames object with results
            frames_obj.face_detection_results = results['face_detection']
            frames_obj.eye_movement_analysis = results['eye_movement']
            frames_obj.head_movement_analysis = results['head_movement']
            frames_obj.multiple_faces_detected = results['multiple_faces_detected']
            frames_obj.suspicious_activity_count = results['suspicious_activity_count']
            frames_obj.save()
            
            return results
            
        except Exception as e:
            print(f"Error in video analysis: {e}")
            return {'error': str(e)}
    
    def analyze_audio_responses(self, interview):
        """Analyze audio responses and generate transcripts"""
        try:
            responses = interview.responses.all()
            all_transcripts = []
            
            for response in responses:
                # Download audio from HDFS
                audio_data = self.hdfs_client.download_file(response.audio_file_path)
                
                # Convert to transcript using Whisper
                transcript = self.transcript_analyzer.audio_to_transcript(audio_data)
                
                # Analyze transcript quality
                analysis = self.transcript_analyzer.analyze_transcript(
                    transcript, 
                    response.question_id
                )
                
                # Update response with results
                response.transcript = transcript
                response.content_score = analysis['content_score']
                response.fluency_score = analysis['fluency_score']
                response.relevance_score = analysis['relevance_score']
                response.save()
                
                all_transcripts.append({
                    'question_id': response.question_id,
                    'transcript': transcript,
                    'analysis': analysis
                })
            
            return {
                'transcripts': all_transcripts,
                'overall_transcript_quality': self.transcript_analyzer.calculate_overall_quality(all_transcripts)
            }
            
        except Exception as e:
            print(f"Error in audio analysis: {e}")
            return {'error': str(e)}
    
    def calculate_overall_score(self, cv_results, transcript_results):
        """Calculate overall interview score"""
        try:
            # Computer vision score (40% weight)
            cv_score = 100 - (cv_results.get('suspicious_activity_count', 0) * 10)
            cv_score = max(0, min(100, cv_score))
            
            # Transcript quality score (60% weight)
            transcript_score = transcript_results.get('overall_transcript_quality', 0)
            
            # Calculate weighted total
            total_score = (cv_score * 0.4) + (transcript_score * 0.6)
            
            return {
                'cv_score': cv_score,
                'transcript_score': transcript_score,
                'total_score': round(total_score, 2),
                'grade': self.get_grade(total_score)
            }
            
        except Exception as e:
            print(f"Error calculating overall score: {e}")
            return {'total_score': 0, 'grade': 'F'}
    
    def get_grade(self, score):
        """Convert score to grade"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
