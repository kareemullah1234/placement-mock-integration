# app.py - Complete Enhanced Audio Analysis API
from flask import Flask, request, jsonify
import os
import json
import logging
import tempfile
import wave
import math
import numpy as np
import speech_recognition as sr
import concurrent.futures
from hdfs import InsecureClient
import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from your Django settings
HDFS_CONFIG = {
    'HOST': os.getenv('HDFS_HOST', '192.168.1.123'),
    'PORT': '9870',
    'USER': 'hdfs'
}

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.123'),
    'database': os.getenv('DB_NAME', 'mock_interview_platform'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'demopass'),
    'port': os.getenv('DB_PORT', '3306')
}

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'your-api-key-here')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class HDFSClient:
    def __init__(self):
        try:
            self.client = InsecureClient(f'http://{HDFS_CONFIG["HOST"]}:{HDFS_CONFIG["PORT"]}/', user=HDFS_CONFIG['USER'])
            self.client.list('/')
            logger.info("HDFS connected successfully")
        except Exception as e:
            logger.error(f"HDFS connection failed: {e}")
            self.client = None

    def get_interview_audio_files(self, interview_info):
        """Get audio files for interview from HDFS using database records"""
        try:
            # First, get the audio file records from database for this interview
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            
            query = """
            SELECT question_id, audio_file_path 
            FROM interview_system_interviewresponse 
            WHERE interview_id = %s
            """
            
            cursor.execute(query, (interview_info['interview_id'],))
            audio_records = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            if not audio_records:
                logger.error(f"No audio records found in database for interview {interview_info['interview_id']}")
                return {}
            
            logger.info(f"Found {len(audio_records)} audio records in database")
            
            # Now check which files actually exist in HDFS
            audio_files = {}
            for record in audio_records:
                question_id = record['question_id']
                hdfs_path = record['audio_file_path']
                
                try:
                    # Check if file exists in HDFS
                    file_status = self.client.status(hdfs_path, strict=False)
                    if file_status:
                        audio_files[question_id] = hdfs_path
                        logger.info(f"Found audio file: {question_id} -> {hdfs_path}")
                    else:
                        logger.warning(f"File not found in HDFS: {hdfs_path}")
                except Exception as e:
                    logger.warning(f"Could not access file {hdfs_path}: {e}")
            
            logger.info(f"Total accessible audio files: {len(audio_files)}")
            return audio_files
            
        except Exception as e:
            logger.error(f"Error getting audio files: {e}")
            return {}

    def download_audio_file(self, hdfs_path):
        """Download audio file from HDFS"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
            with self.client.read(hdfs_path) as reader:
                temp_file.write(reader.read())
            temp_file.close()
            logger.info(f"Downloaded audio file to: {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error downloading {hdfs_path}: {e}")
            return None

class DatabaseClient:
    def get_interview_info(self, interview_id):
        """Get interview and user info from database"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            
            # Query based on your Django models
            query = """
            SELECT 
                i.id as interview_id,
                i.student_id,
                i.attempt_number,
                i.status,
                i.completed_at,
                i.analysis_completed,
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                sp.student_id as student_profile_id
            FROM interview_system_interview i
            JOIN user_management_customuser u ON i.student_id = u.id
            LEFT JOIN user_management_studentprofile sp ON u.id = sp.user_id
            WHERE i.id = %s AND i.status = 'completed' AND i.analysis_completed = FALSE
            """
            
            cursor.execute(query, (interview_id,))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if result:
                logger.info(f"Found interview: {result}")
                # Use student_profile_id if available, otherwise use user id
                result['student_id'] = result['student_profile_id'] or result['id']
            
            return result
        except Error as e:
            logger.error(f"Database error: {e}")
            return None

    def update_analysis_status(self, interview_id, scores=None):
        """Update interview with analysis results"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            
            if scores:
                query = """
                UPDATE interview_system_interview 
                SET analysis_completed = TRUE,
                    overall_score = %s,
                    technical_score = %s,
                    communication_score = %s,
                    confidence_score = %s
                WHERE id = %s
                """
                cursor.execute(query, (
                    scores['overall_score'],
                    scores['technical_score'], 
                    scores['communication_score'],
                    scores['confidence_score'],
                    interview_id
                ))
            else:
                query = "UPDATE interview_system_interview SET analysis_completed = TRUE WHERE id = %s"
                cursor.execute(query, (interview_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            logger.info(f"Updated analysis status for interview {interview_id}")
            return True
        except Error as e:
            logger.error(f"Database update error: {e}")
            return False

class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def enhance_audio(self, input_audio_file, output_audio_file, volume_gain=1.5):
        """Enhanced audio processing function"""
        try:
            with wave.open(input_audio_file, 'rb') as audio:
                params = audio.getparams()
                num_frames = audio.getnframes()

                with wave.open(output_audio_file, 'wb') as output_audio:
                    output_audio.setparams(params)
                    frames_per_read = 8192
                    for _ in range(0, num_frames, frames_per_read):
                        frames = audio.readframes(frames_per_read)
                        if frames:
                            enhanced_frames = self.enhance_audio_frames(frames, params.sampwidth, volume_gain)
                            output_audio.writeframes(enhanced_frames)
            logger.info(f"Enhanced audio saved to: {output_audio_file}")
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            # If enhancement fails, copy original
            import shutil
            shutil.copy2(input_audio_file, output_audio_file)

    def enhance_audio_frames(self, frames, sampwidth, volume_gain):
        """Enhanced frame processing function"""
        if sampwidth == 1:
            audio_samples = np.frombuffer(frames, dtype=np.uint8) - 128
        elif sampwidth == 2:
            audio_samples = np.frombuffer(frames, dtype=np.int16)
        else:
            return frames

        enhanced_samples = (audio_samples * volume_gain).astype(audio_samples.dtype)

        if sampwidth == 1:
            enhanced_samples = np.clip(enhanced_samples + 128, 0, 255)
        elif sampwidth == 2:
            enhanced_samples = np.clip(enhanced_samples, -32768, 32767)

        return enhanced_samples.tobytes()

    def process_audio_chunk(self, chunk_filename, recognizer):
        """Process individual audio chunk"""
        with sr.AudioFile(chunk_filename) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                logger.error(f"Speech recognition error: {e}")
                return "[Error retrieving results]"

    def audio_to_text(self, input_audio_file, chunk_duration=60):
        """Convert audio to text using chunking"""
        try:
            with wave.open(input_audio_file, 'rb') as audio:
                params = audio.getparams()
                frame_rate = params.framerate
                n_channels = params.nchannels
                sampwidth = params.sampwidth
                n_frames = audio.getnframes()

                chunk_size = int(frame_rate * chunk_duration)
                total_chunks = math.ceil(n_frames / chunk_size)

                transcribed_text = []
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []
                    
                    for i in range(total_chunks):
                        chunk_filename = f"temp_chunk_{i}.wav"
                        with wave.open(chunk_filename, 'wb') as chunk:
                            chunk.setnchannels(n_channels)
                            chunk.setsampwidth(sampwidth)
                            chunk.setframerate(frame_rate)
                            frames = audio.readframes(chunk_size)
                            chunk.writeframes(frames)

                        futures.append(executor.submit(self.process_audio_chunk, chunk_filename, self.recognizer))

                    for future in concurrent.futures.as_completed(futures):
                        text = future.result()
                        if text:
                            transcribed_text.append(text)

                # Cleanup temp files
                for i in range(total_chunks):
                    try:
                        os.remove(f"temp_chunk_{i}.wav")
                    except:
                        pass

                return " ".join(transcribed_text)
                
        except Exception as e:
            logger.error(f"Audio to text failed: {e}")
            return ""

    def convert_webm_to_wav(self, webm_path):
        """Convert webm to wav (simple approach)"""
        try:
            wav_path = webm_path.replace('.webm', '.wav')
            
            # Try to read as wav directly (sometimes webm files are actually wav)
            try:
                with wave.open(webm_path, 'rb') as test:
                    test.readframes(1)
                # If successful, just rename
                os.rename(webm_path, wav_path)
                return wav_path
            except:
                # If that fails, try copying and hope for the best
                import shutil
                shutil.copy2(webm_path, wav_path)
                return wav_path
                
        except Exception as e:
            logger.error(f"WebM to WAV conversion failed: {e}")
            return None

class DeepSeekAnalyzer:
    def analyze_responses(self, question_responses):
        """Analyze responses using DeepSeek"""
        try:
            # Create analysis prompt
            prompt = self.create_analysis_prompt(question_responses)
            
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3000
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                parsed_result = self.parse_analysis(analysis)
                logger.info(f"DeepSeek analysis completed successfully")
                return parsed_result
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return self.get_fallback_scores()
                
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return self.get_fallback_scores()

    def create_analysis_prompt(self, question_responses):
        """Create comprehensive analysis prompt for DeepSeek"""
        responses_text = ""
        for question_id, response in question_responses.items():
            # Clean up question_id for better readability
            clean_question = question_id.replace('.wav', '').replace('/', ' - ')
            responses_text += f"Question: {clean_question}\nResponse: {response}\n\n"
        
        return f"""
Analyze this technical interview based on the candidate's responses to various questions across Python, Statistics, and Machine Learning topics:

{responses_text}

Please provide a comprehensive analysis and rate the candidate on a scale of 0-100 for each category:

1. **Technical Knowledge** (0-100): 
   - Accuracy of technical concepts
   - Depth of understanding
   - Correct use of terminology

2. **Communication Skills** (0-100):
   - Clarity of explanations
   - Structure of responses
   - Ability to articulate complex concepts

3. **Confidence Level** (0-100):
   - Confidence in answers
   - Hesitation or uncertainty patterns
   - Overall composure

4. **Overall Performance** (0-100):
   - Combined assessment of all factors
   - Readiness for technical roles
   - Overall interview impression

**IMPORTANT**: Return your response in EXACTLY this JSON format (no additional text):

{{
    "technical_score": <number between 0-100>,
    "communication_score": <number between 0-100>,
    "confidence_score": <number between 0-100>,
    "overall_score": <number between 0-100>,
    "feedback": "Detailed feedback about the candidate's performance, strengths, and areas for improvement"
}}
"""

    def parse_analysis(self, analysis_text):
        """Parse DeepSeek response"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                # Validate that all required fields are present and are numbers
                required_fields = ['technical_score', 'communication_score', 'confidence_score', 'overall_score']
                for field in required_fields:
                    if field not in parsed or not isinstance(parsed[field], (int, float)):
                        logger.warning(f"Missing or invalid field {field}, using fallback")
                        return self.get_fallback_scores()
                
                # Ensure scores are within valid range
                for field in required_fields:
                    parsed[field] = max(0, min(100, float(parsed[field])))
                
                return parsed
            else:
                logger.warning("No JSON found in DeepSeek response, using fallback")
                return self.get_fallback_scores()
        except Exception as e:
            logger.error(f"Error parsing DeepSeek response: {e}")
            return self.get_fallback_scores()

    def get_fallback_scores(self):
        """Fallback scores if analysis fails"""
        return {
            "technical_score": 50.0,
            "communication_score": 50.0,
            "confidence_score": 50.0,
            "overall_score": 50.0,
            "feedback": "Analysis completed with basic scoring due to API limitations"
        }

# Initialize components
hdfs_client = HDFSClient()
db_client = DatabaseClient()
audio_processor = AudioProcessor()
deepseek_analyzer = DeepSeekAnalyzer()

@app.route('/api/analyze-interview/<interview_id>', methods=['POST'])
def analyze_interview(interview_id):
    """Main API endpoint to analyze interview audio"""
    try:
        logger.info(f"Starting analysis for interview {interview_id}")
        
        # Get interview info from database
        interview_info = db_client.get_interview_info(interview_id)
        if not interview_info:
            return jsonify({'error': 'Interview not found or already analyzed'}), 404
        
        # Get audio files from HDFS using database records
        audio_files = hdfs_client.get_interview_audio_files(interview_info)
        if not audio_files:
            return jsonify({'error': 'No audio files found in HDFS'}), 404
        
        # Process each audio file
        question_responses = {}
        processed_count = 0
        
        for question_id, hdfs_path in audio_files.items():
            logger.info(f"Processing question: {question_id}")
            
            try:
                # Download audio from HDFS
                temp_audio = hdfs_client.download_audio_file(hdfs_path)
                if not temp_audio:
                    logger.error(f"Failed to download audio for question {question_id}")
                    continue
                
                # Convert webm to wav
                wav_path = audio_processor.convert_webm_to_wav(temp_audio)
                if not wav_path:
                    logger.error(f"Failed to convert audio for question {question_id}")
                    continue
                
                # Enhance audio
                enhanced_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                audio_processor.enhance_audio(wav_path, enhanced_path)
                
                # Convert to text
                text = audio_processor.audio_to_text(enhanced_path)
                if text and text.strip():
                    question_responses[question_id] = text
                    processed_count += 1
                    logger.info(f"Transcribed {question_id}: {len(text)} characters")
                else:
                    logger.warning(f"No transcription for question {question_id}")
                
                # Cleanup temporary files
                try:
                    os.unlink(wav_path)
                    os.unlink(enhanced_path)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Error processing question {question_id}: {e}")
                continue
        
        if not question_responses:
            return jsonify({'error': 'No audio files could be processed or transcribed'}), 400
        
        logger.info(f"Successfully processed {processed_count} out of {len(audio_files)} audio files")
        
        # Analyze with DeepSeek
        analysis_results = deepseek_analyzer.analyze_responses(question_responses)
        
        # Update database with results
        success = db_client.update_analysis_status(interview_id, analysis_results)
        
        return jsonify({
            'success': success,
            'interview_id': interview_id,
            'total_audio_files': len(audio_files),
            'processed_questions': processed_count,
            'analysis_results': analysis_results,
            'transcriptions': question_responses
        })
        
    except Exception as e:
        logger.error(f"Analysis failed for interview {interview_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pending-interviews', methods=['GET'])
def get_pending_interviews():
    """Get list of interviews ready for analysis"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT id, student_id, attempt_number, completed_at
        FROM interview_system_interview 
        WHERE status = 'completed' AND analysis_completed = FALSE
        ORDER BY completed_at ASC
        LIMIT 50
        """
        
        cursor.execute(query)
        interviews = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        logger.info(f"Found {len(interviews)} pending interviews")
        return jsonify(interviews)
        
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/interview-status/<interview_id>', methods=['GET'])
def get_interview_status(interview_id):
    """Get analysis status for a specific interview"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            id, status, analysis_completed, 
            overall_score, technical_score, communication_score, confidence_score,
            completed_at
        FROM interview_system_interview 
        WHERE id = %s
        """
        
        cursor.execute(query, (interview_id,))
        interview = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        return jsonify(interview)
        
    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_connected = False
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            connection.close()
            db_connected = True
        except:
            pass
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'hdfs': hdfs_client.client is not None,
                'database': db_connected,
                'openrouter': bool(OPENROUTER_API_KEY and OPENROUTER_API_KEY != 'your-api-key-here')
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
