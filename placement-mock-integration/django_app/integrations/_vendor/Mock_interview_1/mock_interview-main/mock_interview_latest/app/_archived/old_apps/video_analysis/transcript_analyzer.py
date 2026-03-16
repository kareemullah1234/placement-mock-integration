import whisper
import requests
import json
import tempfile
import os
from django.conf import settings

class TranscriptAnalyzer:
    def __init__(self):
        self.whisper_model = whisper.load_model("base")
        self.openrouter_config = settings.OPENROUTER_CONFIG
    
    def audio_to_transcript(self, audio_data):
        """Convert audio to transcript using Whisper"""
        try:
            # Save audio data temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(temp_file_path)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return result['text']
            
        except Exception as e:
            print(f"Error in transcription: {e}")
            return ""
    
    def analyze_transcript(self, transcript, question_id):
        """Analyze transcript quality using OpenRouter DeepSeek"""
        try:
            prompt = f"""
            Analyze the following interview response for a technical question.
            
            Question ID: {question_id}
            Response: {transcript}
            
            Please evaluate the response on the following criteria (score 0-100 for each):
            1. Content Quality: Technical accuracy and depth of knowledge
            2. Fluency: Language fluency and communication skills
            3. Relevance: How well the response addresses the question
            
            Provide your analysis in the following JSON format:
            {{
                "content_score": <score>,
                "fluency_score": <score>,
                "relevance_score": <score>,
                "detailed_feedback": "<detailed feedback>",
                "strengths": ["<strength1>", "<strength2>"],
                "improvements": ["<improvement1>", "<improvement2>"]
            }}
            """
            
            headers = {
                'Authorization': f'Bearer {self.openrouter_config["API_KEY"]}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.openrouter_config['MODEL'],
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.3
            }
            
            response = requests.post(
                f"{self.openrouter_config['BASE_URL']}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                try:
                    analysis = json.loads(content)
                    return analysis
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        'content_score': 50,
                        'fluency_score': 50,
                        'relevance_score': 50,
                        'detailed_feedback': content,
                        'strengths': [],
                        'improvements': []
                    }
            else:
                print(f"OpenRouter API error: {response.status_code}")
                return self.fallback_analysis(transcript)
                
        except Exception as e:
            print(f"Error in transcript analysis: {e}")
            return self.fallback_analysis(transcript)
    
    def fallback_analysis(self, transcript):
        """Fallback analysis when API is not available"""
        word_count = len(transcript.split())
        
        # Simple heuristic scoring
        content_score = min(word_count * 2, 100)  # More words = better content
        fluency_score = 70 if word_count > 10 else 40  # Basic fluency check
        relevance_score = 60  # Default relevance
        
        return {
            'content_score': content_score,
            'fluency_score': fluency_score,
            'relevance_score': relevance_score,
            'detailed_feedback': 'Automated analysis - API unavailable',
            'strengths': ['Response provided'],
            'improvements': ['More detailed analysis needed']
        }
    
    def calculate_overall_quality(self, transcripts):
        """Calculate overall transcript quality across all responses"""
        if not transcripts:
            return 0
        
        total_content = sum(t['analysis']['content_score'] for t in transcripts)
        total_fluency = sum(t['analysis']['fluency_score'] for t in transcripts)
        total_relevance = sum(t['analysis']['relevance_score'] for t in transcripts)
        
        count = len(transcripts)
        
        avg_content = total_content / count
        avg_fluency = total_fluency / count
        avg_relevance = total_relevance / count
        
        # Weighted average
        overall_quality = (avg_content * 0.4) + (avg_fluency * 0.3) + (avg_relevance * 0.3)
        
        return round(overall_quality, 2)
