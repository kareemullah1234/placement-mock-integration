import os
import random
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class LocalQuestionService:
    def __init__(self):
        self.questions_root = os.path.join(settings.BASE_DIR, 'questions')
        self.topics = ['Python', 'Statistics', 'Machine-learning']
        self.ensure_questions_directory()
    
    def ensure_questions_directory(self):
        """Ensure questions directory exists"""
        if not os.path.exists(self.questions_root):
            os.makedirs(self.questions_root)
            logger.info(f"Created questions directory: {self.questions_root}")
        
        # Create topic subdirectories
        for topic in self.topics:
            topic_path = os.path.join(self.questions_root, topic)
            if not os.path.exists(topic_path):
                os.makedirs(topic_path)
                logger.info(f"Created topic directory: {topic_path}")
    
    def get_random_questions(self, count=6):
        """Get random questions from local storage"""
        try:
            all_questions = []
            
            for topic in self.topics:
                topic_path = os.path.join(self.questions_root, topic)
                if os.path.exists(topic_path):
                    files = [f for f in os.listdir(topic_path) if f.endswith('.wav')]
                    wav_files = [f"{topic}/{f}" for f in files]
                    
                    # Get up to 2 random questions from each topic
                    if len(wav_files) >= 2:
                        selected = random.sample(wav_files, 2)
                        all_questions.extend(selected)
                    elif wav_files:
                        all_questions.extend(wav_files)
            
            # If no local files, create sample questions
            if not all_questions:
                all_questions = self.create_sample_questions()
            
            return all_questions[:count]
            
        except Exception as e:
            logger.error(f"Error fetching local questions: {e}")
            return self.create_sample_questions()[:count]
    
    def create_sample_questions(self):
        """Create sample question entries when no files exist"""
        return [
            'Python/sample_python_question_1.wav',
            'Python/sample_python_question_2.wav',
            'Statistics/sample_stats_question_1.wav',
            'Statistics/sample_stats_question_2.wav',
            'Machine-learning/sample_ml_question_1.wav',
            'Machine-learning/sample_ml_question_2.wav'
        ]
    
    def get_question_audio(self, question_path):
        """Get audio file from local storage"""
        try:
            full_path = os.path.join(self.questions_root, question_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    return f.read()
            else:
                logger.warning(f"Audio file not found: {full_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading local audio file: {e}")
            return None
    
    def list_questions_in_topic(self, topic):
        """List all questions in a specific topic"""
        try:
            topic_path = os.path.join(self.questions_root, topic)
            if os.path.exists(topic_path):
                return [f for f in os.listdir(topic_path) if f.endswith('.wav')]
            return []
        except Exception as e:
            logger.error(f"Error listing questions in topic {topic}: {e}")
            return []
