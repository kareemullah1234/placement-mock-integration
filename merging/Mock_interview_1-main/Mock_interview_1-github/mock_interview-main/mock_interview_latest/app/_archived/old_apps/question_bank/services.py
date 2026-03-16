import os
import random
from django.conf import settings
from utils.hdfs_client import HDFSClient
from .local_service import LocalQuestionService
import logging

logger = logging.getLogger(__name__)

class QuestionService:
    def __init__(self):
        self.hdfs_client = HDFSClient()
        self.local_service = LocalQuestionService()
        # Enable HDFS by default, fallback to local if HDFS fails
        self.use_local = False

    def get_random_questions(self, count=6):
        """Get random questions - prioritize HDFS, fallback to local"""
        
        # Try HDFS first
        if not self.use_local:
            try:
                if self.hdfs_client.is_connected():
                    logger.info("Fetching random questions from HDFS")
                    questions = self._get_hdfs_questions(count)
                    if questions and len(questions) >= count:
                        logger.info(f"Successfully retrieved {len(questions)} questions from HDFS")
                        return questions
                    else:
                        logger.warning(f"HDFS returned insufficient questions ({len(questions) if questions else 0}), falling back to local")
                else:
                    logger.warning("HDFS not connected, falling back to local storage")
            except Exception as e:
                logger.error(f"HDFS error, falling back to local: {e}")

        # Fallback to local storage
        logger.info("Using local storage for questions")
        return self.local_service.get_random_questions(count)

    def get_question_audio(self, question_path):
        """Get audio file - prioritize HDFS, fallback to local"""
        
        # Try HDFS first
        if not self.use_local:
            try:
                if self.hdfs_client.is_connected():
                    full_path = f"{settings.HDFS_CONFIG['QUESTIONS_DIR']}/{question_path}"
                    logger.info(f"Fetching audio from HDFS: {full_path}")
                    audio_data = self.hdfs_client.download_file(full_path)
                    if audio_data:
                        logger.info(f"Successfully retrieved audio from HDFS: {question_path}")
                        return audio_data
                    else:
                        logger.warning(f"Audio not found in HDFS: {question_path}, falling back to local")
            except Exception as e:
                logger.error(f"HDFS error for audio {question_path}, falling back to local: {e}")

        # Fallback to local storage
        logger.info(f"Using local storage for audio: {question_path}")
        return self.local_service.get_question_audio(question_path)

    def _get_hdfs_questions(self, count=6):
        """Get random questions from HDFS"""
        try:
            topics = ['Python', 'Statistics', 'Machine-learning']
            all_questions = []

            for topic in topics:
                topic_path = f"{settings.HDFS_CONFIG['QUESTIONS_DIR']}/{topic}"
                logger.info(f"Scanning HDFS topic: {topic_path}")
                
                files = self.hdfs_client.list_files(topic_path)
                wav_files = [f"{topic}/{f}" for f in files if f.endswith('.wav')]
                
                logger.info(f"Found {len(wav_files)} .wav files in {topic}")
                
                if wav_files:
                    # Randomly select 2 questions per topic (or all if less than 2)
                    questions_to_select = min(2, len(wav_files))
                    selected = random.sample(wav_files, questions_to_select)
                    all_questions.extend(selected)
                    logger.info(f"Selected {len(selected)} questions from {topic}: {selected}")

            # Shuffle all questions and return the requested count
            if all_questions:
                random.shuffle(all_questions)
                selected_questions = all_questions[:count]
                logger.info(f"Final random selection of {len(selected_questions)} questions: {selected_questions}")
                return selected_questions
            else:
                logger.warning("No questions found in HDFS")
                return []

        except Exception as e:
            logger.error(f"Error getting questions from HDFS: {e}")
            return []
