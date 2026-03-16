from interview_system.models import Interview, InterviewResponse, InterviewFrames
from .models import InterviewReport
import json

class ReportService:
    def generate_detailed_report(self, interview):
        """Generate comprehensive interview report"""
        try:
            # Get or create report
            report, created = InterviewReport.objects.get_or_create(
                interview=interview,
                defaults={
                    'final_grade': self.calculate_grade(interview.overall_score or 0),
                    'technical_score': self.calculate_technical_score(interview),
                    'communication_score': self.calculate_communication_score(interview),
                    'behavioral_score': self.calculate_behavioral_score(interview),
                    'integrity_score': 100 - (interview.cheating_confidence or 0)
                }
            )
            
            # Generate detailed analysis
            report_data = {
                'interview_info': {
                    'student_name': interview.student.get_full_name(),
                    'student_email': interview.student.email,
                    'interview_date': interview.created_at.isoformat(),
                    'duration': self.calculate_duration(interview),
                    'attempt_number': interview.attempt_number
                },
                'scores': {
                    'overall_score': interview.overall_score or 0,
                    'final_grade': report.final_grade,
                    'technical_score': report.technical_score,
                    'communication_score': report.communication_score,
                    'behavioral_score': report.behavioral_score,
                    'integrity_score': report.integrity_score
                },
                'analysis': {
                    'cheating_detected': interview.cheating_detected,
                    'cheating_confidence': interview.cheating_confidence or 0,
                    'suspicious_activities': self.get_suspicious_activities(interview),
                    'response_analysis': self.get_response_analysis(interview),
                    'computer_vision_analysis': self.get_cv_analysis(interview)
                },
                'feedback': {
                    'strengths': report.strengths or [],
                    'areas_for_improvement': report.areas_for_improvement or [],
                    'recommended_resources': report.recommended_resources or [],
                    'overall_feedback': report.overall_feedback or self.generate_overall_feedback(interview)
                }
            }
            
            # Update report if it was created
            if created:
                report.overall_feedback = report_data['feedback']['overall_feedback']
                report.strengths = self.generate_strengths(interview)
                report.areas_for_improvement = self.generate_improvements(interview)
                report.recommended_resources = self.generate_resources(interview)
                report.save()
            
            return report_data
            
        except Exception as e:
            print(f"Error generating report: {e}")
            return {'error': str(e)}
    
    def calculate_grade(self, score):
        """Convert numerical score to letter grade"""
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
    
    def calculate_technical_score(self, interview):
        """Calculate technical competency score"""
        responses = interview.responses.all()
        if not responses:
            return 0
        
        total_content_score = sum(r.content_score or 0 for r in responses)
        return total_content_score / len(responses)
    
    def calculate_communication_score(self, interview):
        """Calculate communication skills score"""
        responses = interview.responses.all()
        if not responses:
            return 0
        
        total_fluency_score = sum(r.fluency_score or 0 for r in responses)
        return total_fluency_score / len(responses)
    
    def calculate_behavioral_score(self, interview):
        """Calculate behavioral assessment score"""
        # Based on computer vision analysis
        if hasattr(interview, 'frames') and interview.frames:
            cv_analysis = interview.frames
            suspicious_ratio = cv_analysis.suspicious_activity_count / max(cv_analysis.total_frames, 1)
            return max(0, 100 - (suspicious_ratio * 100))
        return 75  # Default score
    
    def calculate_duration(self, interview):
        """Calculate interview duration"""
        if interview.started_at and interview.completed_at:
            duration = interview.completed_at - interview.started_at
            return str(duration).split('.')[0]  # Remove microseconds
        return "N/A"
    
    def get_suspicious_activities(self, interview):
        """Get list of suspicious activities detected"""
        activities = []
        
        if hasattr(interview, 'frames') and interview.frames:
            cv_analysis = interview.frames
            
            if cv_analysis.multiple_faces_detected:
                activities.append("Multiple faces detected in video")
            
            if cv_analysis.suspicious_activity_count > 0:
                activities.append(f"{cv_analysis.suspicious_activity_count} suspicious movements detected")
            
            # Parse detailed analysis
            face_detection = cv_analysis.face_detection_results
            if isinstance(face_detection, list):
                face_absent_count = sum(1 for frame in face_detection if frame.get('faces_detected', 0) == 0)
                if face_absent_count > 10:  # More than 10 frames without face
                    activities.append(f"Face not visible in {face_absent_count} frames")
        
        return activities
    
    def get_response_analysis(self, interview):
        """Get detailed response analysis"""
        responses = interview.responses.all()
        analysis = []
        
        for response in responses:
            analysis.append({
                'question_id': response.question_id,
                'transcript': response.transcript[:200] + "..." if len(response.transcript) > 200 else response.transcript,
                'content_score': response.content_score or 0,
                'fluency_score': response.fluency_score or 0,
                'relevance_score': response.relevance_score or 0,
                'word_count': len(response.transcript.split()) if response.transcript else 0
            })
        
        return analysis
    
    def get_cv_analysis(self, interview):
        """Get computer vision analysis summary"""
        if hasattr(interview, 'frames') and interview.frames:
            cv_analysis = interview.frames
            return {
                'total_frames_analyzed': cv_analysis.total_frames,
                'suspicious_activity_count': cv_analysis.suspicious_activity_count,
                'multiple_faces_detected': cv_analysis.multiple_faces_detected,
                'face_detection_summary': self.summarize_face_detection(cv_analysis.face_detection_results)
            }
        return {}
    
    def summarize_face_detection(self, face_detection_results):
        """Summarize face detection results"""
        if not isinstance(face_detection_results, list):
            return {}
        
        total_frames = len(face_detection_results)
        face_detected_frames = sum(1 for frame in face_detection_results if frame.get('faces_detected', 0) > 0)
        multiple_faces_frames = sum(1 for frame in face_detection_results if frame.get('faces_detected', 0) > 1)
        
        return {
            'total_frames': total_frames,
            'face_detection_rate': round((face_detected_frames / max(total_frames, 1)) * 100, 1),
            'multiple_faces_rate': round((multiple_faces_frames / max(total_frames, 1)) * 100, 1)
        }
    
    def generate_overall_feedback(self, interview):
        """Generate overall feedback based on performance"""
        score = interview.overall_score or 0
        
        if score >= 80:
            return "Excellent performance! You demonstrated strong technical knowledge and communication skills."
        elif score >= 60:
            return "Good performance with room for improvement. Focus on technical depth and clarity of communication."
        else:
            return "Needs improvement. Consider reviewing fundamental concepts and practicing communication skills."
    
    def generate_strengths(self, interview):
        """Generate list of strengths"""
        strengths = []
        
        if interview.overall_score and interview.overall_score >= 70:
            strengths.append("Good overall performance")
        
        if not interview.cheating_detected:
            strengths.append("Maintained integrity throughout the interview")
        
        # Analyze responses for strengths
        responses = interview.responses.all()
        if responses:
            avg_fluency = sum(r.fluency_score or 0 for r in responses) / len(responses)
            if avg_fluency >= 70:
                strengths.append("Clear and fluent communication")
        
        return strengths or ["Completed the interview process"]
    
    def generate_improvements(self, interview):
        """Generate areas for improvement"""
        improvements = []
        
        if interview.cheating_detected:
            improvements.append("Maintain proper interview etiquette and avoid suspicious behavior")
        
        responses = interview.responses.all()
        if responses:
            avg_content = sum(r.content_score or 0 for r in responses) / len(responses)
            if avg_content < 60:
                improvements.append("Strengthen technical knowledge and provide more detailed answers")
            
            avg_relevance = sum(r.relevance_score or 0 for r in responses) / len(responses)
            if avg_relevance < 60:
                improvements.append("Focus on answering questions more directly and relevantly")
        
        return improvements or ["Continue practicing interview skills"]
    
    def generate_resources(self, interview):
        """Generate recommended learning resources"""
        resources = [
            "Practice coding problems on LeetCode or HackerRank",
            "Review fundamental computer science concepts",
            "Practice mock interviews with peers or mentors",
            "Improve communication skills through public speaking practice"
        ]
        
        # Customize based on performance
        if interview.cheating_detected:
            resources.insert(0, "Review interview ethics and professional conduct guidelines")
        
        return resources
