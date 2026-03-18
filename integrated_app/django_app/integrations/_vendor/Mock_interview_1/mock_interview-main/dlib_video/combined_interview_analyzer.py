#!/usr/bin/env python3
"""
Combined Interview Analysis System
Integrates frame analysis (dlib container) with speech analysis to provide comprehensive interview assessment
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
import mysql.connector
from kafka import KafkaConsumer, TopicPartition
from collections import defaultdict, deque
import math
import subprocess
import tempfile
import statistics
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Enhanced libraries for analysis
try:
    import dlib
    import mediapipe as mp
    from scipy.spatial.distance import euclidean
    from sklearn.preprocessing import StandardScaler
    ADVANCED_LIBS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Advanced libraries not available: {e}")
    ADVANCED_LIBS_AVAILABLE = False

# Speech analysis libraries
try:
    import librosa
    import soundfile as sf
    HAS_LIBROSA = True
    print("✓ Librosa available")
except ImportError:
    print("⚠ Librosa not available")
    HAS_LIBROSA = False

try:
    import opensmile
    HAS_OPENSMILE = True
    print("✓ OpenSMILE available")
except ImportError:
    print("⚠ OpenSMILE not available")
    HAS_OPENSMILE = False

try:
    import parselmouth
    from parselmouth.praat import call
    HAS_PRAAT = True
    print("✓ Praat available")
except ImportError:
    print("⚠ Praat not available")
    HAS_PRAAT = False

try:
    from scipy.signal import find_peaks
    HAS_SCIPY = True
    print("✓ SciPy available")
except ImportError:
    print("⚠ SciPy not available")
    HAS_SCIPY = False

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/combined_interview_analysis.log')
    ]
)
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
    'bootstrap_servers': ['127.0.0.1:9092'],  # ✅ FIXED
    'auto_offset_reset': 'earliest',
    'consumer_timeout_ms': 150000,
    'group_id': None,
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore')),
    'enable_auto_commit': False,
    'max_poll_records': 100
}

# Speech Analysis Class (adapted from your QuickAgent script)
class StreamlinedSpeechAnalyzer:
    def __init__(self):
        self.sample_rate = 16000
        self.smile = None
        self.audio_files_processed = 0  # ADD THIS LINE
        
        if HAS_OPENSMILE:
            try:
                self.smile = opensmile.Smile(
                    feature_set=opensmile.FeatureSet.eGeMAPSv02,
                    feature_level=opensmile.FeatureLevel.Functionals,
                )
                print("✓ OpenSMILE initialized")
            except Exception as e:
                print(f"⚠ OpenSMILE failed: {e}")
                self.smile = None

    def analyze_audio_file(self, audio_path):
        """Analyze single audio file"""
        try:
            if not HAS_LIBROSA:
                return self._empty_analysis()

            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            if len(audio) == 0:
                return self._empty_analysis()

            duration = len(audio) / sr

            # Core analysis
            basic_metrics = self._get_basic_metrics(audio, sr)
            praat_metrics = self._get_praat_metrics(audio_path)
            opensmile_metrics = self._get_opensmile_metrics(audio_path)

            # Assessment
            assessment = self._assess_speech(basic_metrics, praat_metrics, opensmile_metrics)

            # Behavioral insights
            behavioral = self._generate_behavioral_insights(assessment, praat_metrics, basic_metrics)

            return {
                "file_path": str(audio_path),
                "duration_seconds": round(duration, 2),
                "speaking": assessment["speaking"],
                "clarity": assessment["clarity"],
                "pace": assessment["pace"],
                "confidence_scores": assessment["confidence"],
                "behavioral_analysis": behavioral,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return self._error_analysis(str(audio_path), "Analysis failed")

    def _get_basic_metrics(self, audio, sr):
        """Extract basic metrics from audio"""
        # Voice activity
        energy = librosa.feature.rms(y=audio, hop_length=512)[0]
        energy_threshold = np.mean(energy) + 0.5 * np.std(energy)
        speech_frames = energy > energy_threshold
        speaking_ratio = np.sum(speech_frames) / len(speech_frames)

        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(audio)[0]

        # Pace estimation
        if HAS_SCIPY:
            peaks, _ = find_peaks(energy, height=np.mean(energy) * 0.5, distance=int(sr/512/4))
            estimated_syllables = len(peaks)
        else:
            estimated_syllables = int(speaking_ratio * len(speech_frames) * 0.08)

        duration = len(audio) / sr
        wpm = (estimated_syllables / 1.5 / duration) * 60 if duration > 0 else 0

        return {
            "speaking_ratio": float(speaking_ratio),
            "spectral_centroid_mean": float(np.mean(spectral_centroid)),
            "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
            "zero_crossing_rate": float(np.mean(zcr)),
            "energy_mean": float(np.mean(energy)),
            "estimated_wpm": float(wpm),
            "speech_segments": int(self._count_segments(speech_frames))
        }

    def _get_praat_metrics(self, audio_path):
        """Extract key Praat metrics"""
        if not HAS_PRAAT:
            return {"error": "Praat not available"}

        try:
            sound = parselmouth.Sound(str(audio_path))

            # Pitch analysis
            pitch = sound.to_pitch()
            f0_values = pitch.selected_array['frequency']
            f0_values = f0_values[f0_values != 0]

            if len(f0_values) == 0:
                return {"error": "No voiced segments found"}

            # Intensity
            intensity = sound.to_intensity()
            intensity_values = intensity.values.T[0]
            intensity_mean = float(np.mean(intensity_values))
            intensity_std = float(np.std(intensity_values))

            # Harmonicity
            harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            harmonicity_mean = call(harmonicity, "Get mean", 0, 0)

            # Voice quality measures
            pointProcess = call(sound, "To PointProcess (periodic, cc)", 75, 600)
            jitter = call(pointProcess, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
            shimmer = call([sound, pointProcess], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

            # Speaking rate estimation
            speaking_rate = len(f0_values) / sound.duration * 2.0 if sound.duration > 0 else 0

            result = {
                "f0_mean": float(np.mean(f0_values)),
                "f0_std": float(np.std(f0_values)),
                "f0_range": float(np.max(f0_values) - np.min(f0_values)),
                "mean_intensity": intensity_mean,
                "intensity_std": intensity_std,
                "speaking_rate": float(speaking_rate)
            }

            # Add voice quality only if valid
            if not np.isnan(harmonicity_mean):
                result["harmonicity_mean"] = float(harmonicity_mean)

            if not np.isnan(jitter) and jitter > 0:
                result["jitter_percent"] = float(jitter * 100)

            if not np.isnan(shimmer) and shimmer > 0:
                result["shimmer_percent"] = float(shimmer * 100)

            return result

        except Exception as e:
            return {"error": f"Praat analysis failed"}

    def _get_opensmile_metrics(self, audio_path):
        """Extract key OpenSMILE metrics"""
        if not self.smile:
            return {"error": "OpenSMILE not available"}

        try:
            features = self.smile.process_file(str(audio_path))

            if features.empty:
                return {"error": "No features"}

            key_metrics = {}
            for col in features.columns:
                values = features[col].values
                if len(values) > 0 and not np.isnan(values[0]):
                    if any(x in col.lower() for x in ['f0', 'jitter', 'shimmer', 'hnr', 'loudness']):
                        key_metrics[col] = float(values[0])

            return key_metrics

        except Exception as e:
            return {"error": "OpenSMILE failed"}

    def _assess_speech(self, basic, praat, opensmile):
        """Assess speech quality"""
        speaking_score = basic["speaking_ratio"]
        speaking = speaking_score > 0.15

        # CLARITY ASSESSMENT
        clarity_score = 0.5
        clarity_confidence = 0

        # From Praat
        if "error" not in praat:
            jitter_score = max(0, 1 - (praat.get("jitter_percent", 2.0) / 2.0))
            shimmer_score = max(0, 1 - (praat.get("shimmer_percent", 8.0) / 8.0))
            clarity_score += (jitter_score + shimmer_score) * 0.3
            clarity_confidence += 0.3

            harm_score = min(1.0, max(0, (praat.get("harmonicity_mean", 0) + 5) / 15))
            clarity_score += harm_score * 0.3
            clarity_confidence += 0.3

        # From spectral features
        sc = basic["spectral_centroid_mean"]
        if 1000 <= sc <= 4000:
            sc_score = 1.0 - abs(sc - 2500) / 1500
        else:
            sc_score = 0.3
        clarity_score += sc_score * 0.2
        clarity_confidence += 0.2

        zcr_score = max(0, 1 - (basic["zero_crossing_rate"] - 0.1) / 0.15)
        clarity_score += zcr_score * 0.2
        clarity_confidence += 0.2

        final_clarity_score = clarity_score / clarity_confidence if clarity_confidence > 0 else 0.5

        if final_clarity_score > 0.7:
            clarity = "good"
        elif final_clarity_score > 0.5:
            clarity = "fair"
        else:
            clarity = "poor"

        # PACE ASSESSMENT
        pace = "normal"
        pace_confidence = 0.6

        if "error" not in praat and praat.get("speaking_rate", 0) > 0:
            rate = praat["speaking_rate"]
            if rate < 2.5:
                pace = "slow"
            elif rate > 4.5:
                pace = "fast"
            else:
                pace = "normal"
            pace_confidence = 0.8
        else:
            wpm = basic["estimated_wpm"]
            if wpm < 120:
                pace = "slow"
            elif wpm > 180:
                pace = "fast"
            pace_confidence = 0.5

        return {
            "speaking": speaking,
            "clarity": clarity,
            "pace": pace,
            "confidence": {
                "speaking_confidence": round(0.8, 2),
                "clarity_confidence": round(clarity_confidence, 2),
                "clarity_score": round(final_clarity_score, 3),
                "pace_confidence": round(pace_confidence, 2)
            }
        }

    def _generate_behavioral_insights(self, assessment, praat, basic):
        """Generate behavioral insights"""
        clarity_score = assessment["confidence"]["clarity_score"]
        speaking_ratio = basic["speaking_ratio"]

        if clarity_score > 0.7 and speaking_ratio > 0.5:
            confidence_score = 0.85
            confidence_level = "High"
            confidence_indicators = [
                "Clear voice quality indicates confidence",
                "Good speech activity suggests engagement",
                "Stable voice parameters show composure"
            ]
        elif clarity_score > 0.5 and speaking_ratio > 0.2:
            confidence_score = 0.6
            confidence_level = "Moderate"
            confidence_indicators = [
                "Moderate voice clarity",
                "Some hesitation detected"
            ]
        else:
            confidence_score = 0.3
            confidence_level = "Low"
            confidence_indicators = [
                "Limited voice activity may indicate low confidence",
                "Voice quality suggests nervousness"
            ]

        # Stress indicators
        stress_indicators = []
        stress_level = 0.0
        if "error" not in praat:
            if praat.get("jitter_percent", 0) > 1.5:
                stress_indicators.append("Voice tremor detected")
                stress_level += 0.3
            if praat.get("shimmer_percent", 0) > 6.0:
                stress_indicators.append("Voice instability detected")
                stress_level += 0.2

        # Engagement
        engagement_level = min(0.9, speaking_ratio * 3)
        if engagement_level > 0.7:
            engagement_category = "High"
            engagement_indicators = ["High voice activity suggests strong engagement"]
        elif engagement_level > 0.4:
            engagement_category = "Moderate"
            engagement_indicators = ["Moderate engagement levels"]
        else:
            engagement_category = "Low"
            engagement_indicators = ["Low voice activity may indicate disengagement"]

        # Interview performance
        if confidence_score > 0.7 and engagement_level > 0.6:
            performance_score = 0.85
            performance_level = "Excellent"
            performance_indicators = [
                "Clear voice quality enhances message delivery",
                "Good engagement level shows readiness"
            ]
        elif confidence_score > 0.5:
            performance_score = 0.65
            performance_level = "Good"
            performance_indicators = [
                "Adequate voice clarity for interview",
                "Room for improvement in engagement"
            ]
        else:
            performance_score = 0.4
            performance_level = "Needs Improvement"
            performance_indicators = [
                "Voice clarity could be enhanced",
                "Low engagement suggests nervousness"
            ]

        return {
            "confidence_indicators": {
                "confidence_score": confidence_score,
                "confidence_level": confidence_level,
                "indicators": confidence_indicators,
                "key_metrics": {
                    "pitch_variation": praat.get("f0_std", 0) if "error" not in praat else 0,
                    "speaking_rate": praat.get("speaking_rate", 0) if "error" not in praat else 0,
                    "voice_stability": praat.get("jitter_percent", 0) if "error" not in praat else 0
                }
            },
            "emotional_state": {
                "arousal_level": 0.5,
                "valence": 0.5,
                "emotional_state": "neutral/balanced",
                "indicators": [],
                "dominant_emotions": ["neutral"]
            },
            "stress_anxiety_levels": {
                "stress_level": stress_level,
                "stress_category": "High" if stress_level > 0.6 else "Moderate" if stress_level > 0.3 else "Low",
                "indicators": stress_indicators,
                "physiological_signs": []
            },
            "engagement_level": {
                "engagement_level": engagement_level,
                "engagement_category": engagement_category,
                "indicators": engagement_indicators
            },
            "communication_style": {
                "extroversion_score": min(0.8, speaking_ratio * 2),
                "communication_style": "balanced/adaptive",
                "style_indicators": []
            },
            "personality_traits": {
                "conscientiousness": 0.7,
                "neuroticism": stress_level,
                "openness": 0.6,
                "trait_descriptions": {
                    "conscientiousness": "organized, disciplined, and reliable",
                    "neuroticism": "typical emotional range",
                    "openness": "creative, curious, and expressive"
                }
            },
            "interview_performance": {
                "interview_performance_score": performance_score,
                "performance_level": performance_level,
                "indicators": performance_indicators,
                "recommendations": []
            }
        }

    def _count_segments(self, frames):
        segments = 0
        in_speech = False
        for frame in frames:
            if frame and not in_speech:
                segments += 1
                in_speech = True
            elif not frame:
                in_speech = False
        return segments

    def _empty_analysis(self):
        return {
            "speaking": False,
            "clarity": "poor",
            "pace": "normal",
            "confidence_scores": {},
            "behavioral_analysis": {},
            "error": "Empty audio file"
        }

    def _error_analysis(self, file_path, error_msg):
        return {
            "file_path": file_path,
            "speaking": False,
            "clarity": "poor",
            "pace": "normal",
            "confidence_scores": {},
            "behavioral_analysis": {},
            "error": error_msg,
            "analysis_timestamp": datetime.now().isoformat()
        }

    def analyze_session_directory(self, session_dir):
        """Analyze all audio files in session directory - FIXED to avoid duplicates"""
        try:
            session_path = Path(session_dir)
            if not session_path.exists():
                return {"error": f"Session directory {session_dir} does not exist"}

            # Find audio files - prioritize .wav over .webm to avoid duplicates
            wav_files = list(session_path.glob("*.wav"))
            webm_files = list(session_path.glob("*.webm"))
            
            # Use .wav files if they exist, otherwise use .webm files
            if wav_files:
                audio_files = wav_files
                logger.info(f"Using {len(wav_files)} converted .wav files")
            else:
                audio_files = webm_files
                logger.info(f"Using {len(webm_files)} original .webm files")
            
            # Add other formats
            for ext in ['*.mp3', '*.m4a', '*.flac']:
                audio_files.extend(session_path.glob(ext))

            if not audio_files:
                return {"error": f"No audio files found in {session_dir}"}

            logger.info(f"Analyzing {len(audio_files)} audio files...")

            # Analyze files
            analyses = []
            for i, audio_file in enumerate(audio_files, 1):
                logger.info(f"Processing audio {i}/{len(audio_files)}: {audio_file.name}")
                analysis = self.analyze_audio_file(audio_file)
                analyses.append(analysis)
                self.audio_files_processed += 1

            # Generate summary
            session_summary = self._generate_session_summary(analyses)

            return {
                "session_summary": session_summary,
                "audio_analyses": analyses
            }

        except Exception as e:
            logger.error(f"Error analyzing session directory: {e}")
            return {"error": str(e)}

    def _generate_session_summary(self, analyses):
        """Generate session summary from all audio analyses"""
        valid_analyses = [a for a in analyses if "error" not in a]
        if not valid_analyses:
            return {"error": "No valid analyses"}

        # Basic stats
        speaking_segments = [a for a in valid_analyses if a["speaking"]]
        total_duration = sum(a.get("duration_seconds", 0) for a in valid_analyses)
        speaking_duration = sum(a.get("duration_seconds", 0) for a in speaking_segments)

        # Quality distributions
        clarity_counts = {"good": 0, "fair": 0, "poor": 0}
        pace_counts = {"slow": 0, "normal": 0, "fast": 0}

        for analysis in valid_analyses:
            clarity_counts[analysis["clarity"]] += 1
            pace_counts[analysis["pace"]] += 1

        return {
            "overall_speaking": len(speaking_segments) > 0,
            "overall_clarity": max(clarity_counts, key=clarity_counts.get),
            "overall_pace": max(pace_counts, key=pace_counts.get),
            "aggregated_metrics": {
                "total_duration": round(total_duration, 2),
                "speaking_duration": round(speaking_duration, 1),
                "total_audio_files": len(valid_analyses),
                "speaking_files": len(speaking_segments)
            },
            "quality_distribution": {
                "clarity": clarity_counts,
                "pace": pace_counts
            }
        }


# Frame Analysis Class (from your dlib container)
class AdvancedFrameAnalyzer:
    def __init__(self):
        self.face_detector = None
        self.landmark_predictor = None
        self.mp_face_mesh = None
        self.mp_drawing = None
        self.emotion_history = deque(maxlen=30)
        self.gaze_history = deque(maxlen=20)
        self.confidence_metrics = deque(maxlen=50)
        self.head_tilt_history = deque(maxlen=15)

        if ADVANCED_LIBS_AVAILABLE:
            self._initialize_advanced_models()

    def _initialize_advanced_models(self):
        """Initialize dlib and MediaPipe models"""
        try:
            self.face_detector = dlib.get_frontal_face_detector()

            predictor_paths = [
                "/app/open_cv/shape_predictor_68_face_landmarks.dat",
                "/tmp/shape_predictor_68_face_landmarks.dat",
                "/app/models/shape_predictor_68_face_landmarks.dat",
                "./shape_predictor_68_face_landmarks.dat"
            ]

            predictor_found = False
            for predictor_path in predictor_paths:
                if os.path.exists(predictor_path):
                    try:
                        self.landmark_predictor = dlib.shape_predictor(predictor_path)
                        logger.info(f"✅ Dlib landmark predictor loaded from: {predictor_path}")
                        predictor_found = True
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load predictor from {predictor_path}: {e}")
                        continue

            if not predictor_found:
                logger.warning("⚠️ Dlib landmark predictor not found")

            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.mp_drawing = mp.solutions.drawing_utils
            logger.info("✅ MediaPipe face mesh initialized")

        except Exception as e:
            logger.error(f"❌ Error initializing advanced models: {e}")

    def analyze_frame_comprehensive(self, frame, frame_number, timestamp):
        """Comprehensive frame analysis"""
        try:
            analysis = {
                "frame_metadata": {
                    "frame_number": frame_number,
                    "timestamp": timestamp
                }
            }

            face_data = self._detect_faces(frame)
            analysis["face_detection"] = face_data

            if face_data["face_present"]:
                analysis["eye_gaze_analysis"] = self._analyze_eye_gaze_llm_friendly(frame)
                analysis["emotion_analysis"] = self._analyze_emotions_llm_friendly(frame)
                analysis["posture_analysis"] = self._analyze_posture_llm_friendly(frame)
                analysis["body_language"] = self._analyze_body_language_llm_friendly(frame)
                analysis["attention_focus"] = self._assess_attention_focus_simple(analysis)

            return analysis

        except Exception as e:
            logger.error(f"❌ Error in frame analysis: {e}")
            return self._create_error_frame_data(frame_number, timestamp)

    def _detect_faces(self, frame):
        """Face detection"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if ADVANCED_LIBS_AVAILABLE and self.face_detector:
                faces = self.face_detector(gray)
                faces_detected = len(faces)
            else:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                faces_detected = len(faces)

            return {
                "faces_detected": faces_detected,
                "face_present": faces_detected > 0,
                "multiple_people": faces_detected > 1
            }

        except Exception as e:
            logger.error(f"❌ Face detection error: {e}")
            return {"faces_detected": 0, "face_present": False, "multiple_people": False}

    def _analyze_eye_gaze_llm_friendly(self, frame):
        """Eye gaze analysis"""
        try:
            if not ADVANCED_LIBS_AVAILABLE or not self.landmark_predictor:
                return self._basic_gaze_analysis_llm_friendly(frame)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_detector(gray)

            if len(faces) == 0:
                return {
                    "eye_gaze_direction": "no_face_detected",
                    "eyes_closed": False,
                    "gaze_quality": "no_face"
                }

            landmarks = self.landmark_predictor(gray, faces[0])

            # Eye region landmarks
            left_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)]
            right_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)]

            # Calculate eye aspect ratio
            ear_left = self._calculate_eye_aspect_ratio(left_eye_points)
            ear_right = self._calculate_eye_aspect_ratio(right_eye_points)
            avg_ear = (ear_left + ear_right) / 2.0

            eyes_closed = avg_ear < 0.2

            # Estimate gaze direction
            face_center_x = (faces[0].left() + faces[0].right()) // 2
            left_eye_center = np.mean(left_eye_points, axis=0)
            right_eye_center = np.mean(right_eye_points, axis=0)
            eye_center_x = (left_eye_center[0] + right_eye_center[0]) / 2

            gaze_offset = abs(eye_center_x - face_center_x)
            max_offset = faces[0].width() * 0.15

            if eyes_closed:
                gaze_direction = "eyes_closed"
                gaze_quality = "eyes_closed"
            elif gaze_offset < max_offset * 0.5:
                gaze_direction = "looking_at_camera"
                gaze_quality = "direct_eye_contact"
            elif eye_center_x < face_center_x - max_offset:
                gaze_direction = "looking_left"
                gaze_quality = "looking_away"
            elif eye_center_x > face_center_x + max_offset:
                gaze_direction = "looking_right"
                gaze_quality = "looking_away"
            else:
                gaze_direction = "gaze_averted"
                gaze_quality = "distracted"

            is_looking_at_camera = gaze_direction == "looking_at_camera"
            self.gaze_history.append(is_looking_at_camera)

            return {
                "eye_gaze_direction": gaze_direction,
                "eyes_closed": eyes_closed,
                "gaze_quality": gaze_quality
            }

        except Exception as e:
            logger.error(f"❌ Eye gaze analysis error: {e}")
            return self._basic_gaze_analysis_llm_friendly(frame)

    def _calculate_eye_aspect_ratio(self, eye_points):
        """Calculate Eye Aspect Ratio"""
        try:
            A = euclidean(eye_points[1], eye_points[5])
            B = euclidean(eye_points[2], eye_points[4])
            C = euclidean(eye_points[0], eye_points[3])
            ear = (A + B) / (2.0 * C)
            return ear
        except:
            return 0.25

    def _analyze_emotions_llm_friendly(self, frame):
        """Emotion analysis"""
        try:
            dominant_emotion = self._detect_primary_emotion_categories(frame)
            micro_expressions = self._detect_micro_expressions_simple(frame, dominant_emotion)

            self.emotion_history.append(dominant_emotion)
            emotion_variability = self._calculate_emotion_variability_simple()

            return {
                "dominant_emotion": dominant_emotion,
                "micro_expressions": micro_expressions,
                "emotion_stability": emotion_variability
            }

        except Exception as e:
            logger.error(f"❌ Emotion analysis error: {e}")
            return {
                "dominant_emotion": "neutral",
                "micro_expressions": ["neutral"],
                "emotion_stability": "unknown"
            }

    def _detect_primary_emotion_categories(self, frame):
        """Detect primary emotion"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            smile_cascade_paths = [
                "/app/open_cv/haarcascade_smile.xml",
                cv2.data.haarcascades + 'haarcascade_smile.xml'
            ]

            smile_cascade = None
            for path in smile_cascade_paths:
                if os.path.exists(path):
                    smile_cascade = cv2.CascadeClassifier(path)
                    break

            if smile_cascade and not smile_cascade.empty():
                smiles = smile_cascade.detectMultiScale(gray, 1.8, 20)
                if len(smiles) > 0:
                    return "happiness"

            # Enhanced emotion detection using facial landmarks
            if ADVANCED_LIBS_AVAILABLE and self.landmark_predictor:
                faces = self.face_detector(gray)
                if len(faces) > 0:
                    landmarks = self.landmark_predictor(gray, faces[0])
                    emotion = self._analyze_emotion_from_landmarks(landmarks)
                    if emotion != "neutral":
                        return emotion

            return "neutral"

        except Exception as e:
            logger.error(f"❌ Primary emotion detection error: {e}")
            return "neutral"

    def _analyze_emotion_from_landmarks(self, landmarks):
        """Analyze emotion from facial landmarks"""
        try:
            # Mouth analysis
            mouth_left = (landmarks.part(48).x, landmarks.part(48).y)
            mouth_right = (landmarks.part(54).x, landmarks.part(54).y)
            mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
            mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)

            mouth_width = euclidean(mouth_left, mouth_right)
            mouth_height = euclidean(mouth_top, mouth_bottom)
            mouth_ratio = mouth_width / mouth_height if mouth_height > 0 else 0

            # Eyebrow analysis
            left_eyebrow_inner = (landmarks.part(21).x, landmarks.part(21).y)
            right_eyebrow_inner = (landmarks.part(22).x, landmarks.part(22).y)

            # Eye analysis
            left_eye_top = (landmarks.part(37).x, landmarks.part(37).y)
            left_eye_bottom = (landmarks.part(41).x, landmarks.part(41).y)
            right_eye_top = (landmarks.part(44).x, landmarks.part(44).y)
            right_eye_bottom = (landmarks.part(46).x, landmarks.part(46).y)

            eye_openness = (euclidean(left_eye_top, left_eye_bottom) + euclidean(right_eye_top, right_eye_bottom)) / 2

            # Simple emotion classification
            if mouth_ratio > 3.5:
                return "happiness"
            elif mouth_ratio < 2.5:
                return "sadness"
            elif eye_openness > 15:
                return "surprise"
            elif left_eyebrow_inner[1] < left_eye_top[1] - 10:
                return "surprise"
            elif left_eyebrow_inner[1] > left_eye_top[1] - 5:
                return "anger"
            else:
                return "neutral"

        except Exception as e:
            logger.error(f"❌ Landmark emotion analysis error: {e}")
            return "neutral"

    def _detect_micro_expressions_simple(self, frame, primary_emotion):
        """Simple micro-expression detection"""
        try:
            micro_expressions = []

            if primary_emotion == "happiness":
                micro_expressions = ["genuine_smile"]
            elif primary_emotion == "sadness":
                micro_expressions = ["slight_frown"]
            elif primary_emotion == "anger":
                micro_expressions = ["tense_jaw", "furrowed_brow"]
            elif primary_emotion == "surprise":
                micro_expressions = ["raised_eyebrows", "wide_eyes"]
            elif primary_emotion == "fear":
                micro_expressions = ["tense_expression"]
            elif primary_emotion == "disgust":
                micro_expressions = ["nose_wrinkle"]
            else:
                micro_expressions = ["relaxed_expression"]

            return micro_expressions

        except Exception as e:
            logger.error(f"❌ Micro-expression detection error: {e}")
            return ["neutral"]

    def _calculate_emotion_variability_simple(self):
        """Simple emotion variability"""
        if len(self.emotion_history) < 5:
            return "insufficient_data"

        unique_emotions = len(set(self.emotion_history))
        if unique_emotions == 1:
            return "very_stable"
        elif unique_emotions <= 2:
            return "stable"
        elif unique_emotions <= 3:
            return "variable"
        else:
            return "highly_variable"

    def _analyze_posture_llm_friendly(self, frame):
        """Posture analysis"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if ADVANCED_LIBS_AVAILABLE and self.face_detector:
                faces = self.face_detector(gray)
            else:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                faces = [cv2.Rect(x, y, w, h) for x, y, w, h in faces]

            if len(faces) == 0:
                return {
                    "face_centering": "no_face",
                    "posture_stability": "unknown"
                }

            face = faces[0]
            frame_height, frame_width = frame.shape[:2]

            # Face centering analysis
            if hasattr(face, 'center'):
                face_center_x = face.center().x
            else:
                face_center_x = face[0] + (face[2] if len(face) > 2 else face.width()) // 2

            frame_center_x = frame_width // 2
            centering_offset = abs(face_center_x - frame_center_x) / frame_width

            if centering_offset < 0.08:
                face_centering = "well_centered"
            elif centering_offset < 0.15:
                face_centering = "slightly_off_center"
            else:
                face_centering = "poorly_positioned"

            return {
                "face_centering": face_centering,
                "posture_stability": "stable"
            }

        except Exception as e:
            logger.error(f"❌ Posture analysis error: {e}")
            return {
                "face_centering": "unknown",
                "posture_stability": "unknown"
            }

    def _analyze_body_language_llm_friendly(self, frame):
        """Body language analysis"""
        try:
            if not ADVANCED_LIBS_AVAILABLE or not self.landmark_predictor:
                return {
                    "head_tilt": "straight",
                    "head_movement": "minimal"
                }

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_detector(gray)

            if len(faces) == 0:
                return {
                    "head_tilt": "unknown",
                    "head_movement": "unknown"
                }

            landmarks = self.landmark_predictor(gray, faces[0])

            # Calculate head tilt
            left_eye = (landmarks.part(36).x, landmarks.part(36).y)
            right_eye = (landmarks.part(45).x, landmarks.part(45).y)

            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            angle = math.degrees(math.atan2(dy, dx))

            # Classify head tilt
            if abs(angle) < 5:
                head_tilt = "straight"
            elif 5 <= angle <= 20:
                head_tilt = "slightly_right"
            elif angle > 20:
                head_tilt = "tilted_right"
            elif -20 <= angle <= -5:
                head_tilt = "slightly_left"
            else:
                head_tilt = "tilted_left"

            # Track head movement
            self.head_tilt_history.append(angle)
            head_movement = self._calculate_head_movement_simple()

            return {
                "head_tilt": head_tilt,
                "head_movement": head_movement
            }

        except Exception as e:
            logger.error(f"❌ Body language analysis error: {e}")
            return {
                "head_tilt": "straight",
                "head_movement": "minimal"
            }

    def _calculate_head_movement_simple(self):
        """Simple head movement calculation"""
        if len(self.head_tilt_history) < 3:
            return "insufficient_data"

        recent_tilts = list(self.head_tilt_history)[-5:]
        mean_tilt = sum(recent_tilts) / len(recent_tilts)
        variance = sum((x - mean_tilt) ** 2 for x in recent_tilts) / len(recent_tilts)

        if variance < 5:
            return "very_stable"
        elif variance < 15:
            return "stable"
        elif variance < 30:
            return "moderate_movement"
        else:
            return "high_movement"

    def _assess_attention_focus_simple(self, analysis):
        """Simple attention and focus assessment"""
        try:
            eye_gaze = analysis.get("eye_gaze_analysis", {})
            body_lang = analysis.get("body_language", {})
            posture = analysis.get("posture_analysis", {})

            looking_away = eye_gaze.get("eye_gaze_direction") in ["looking_left", "looking_right", "gaze_averted", "eyes_closed"]

            distraction_present = (
                looking_away or
                posture.get("face_centering") == "poorly_positioned" or
                body_lang.get("head_movement") in ["moderate_movement", "high_movement"]
            )

            if eye_gaze.get("eye_gaze_direction") == "looking_at_camera" and not distraction_present:
                attention_level = "focused"
            elif looking_away:
                attention_level = "distracted"
            elif distraction_present:
                attention_level = "somewhat_distracted"
            else:
                attention_level = "moderately_focused"

            return {
                "attention_level": attention_level,
                "looking_away": looking_away,
                "distraction_present": distraction_present
            }

        except Exception as e:
            logger.error(f"❌ Attention focus assessment error: {e}")
            return {
                "attention_level": "unknown",
                "looking_away": False,
                "distraction_present": False
            }

    def _basic_gaze_analysis_llm_friendly(self, frame):
        """Basic gaze analysis fallback"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, 1.3, 5)

            if len(eyes) >= 2:
                return {
                    "eye_gaze_direction": "looking_at_camera",
                    "eyes_closed": False,
                    "gaze_quality": "direct_eye_contact"
                }
            elif len(eyes) == 1:
                return {
                    "eye_gaze_direction": "partially_visible",
                    "eyes_closed": False,
                    "gaze_quality": "unclear"
                }
            else:
                return {
                    "eye_gaze_direction": "eyes_not_detected",
                    "eyes_closed": True,
                    "gaze_quality": "eyes_closed"
                }

        except Exception as e:
            logger.error(f"❌ Basic gaze analysis error: {e}")
            return {
                "eye_gaze_direction": "unknown",
                "eyes_closed": False,
                "gaze_quality": "unknown"
            }

    def _create_error_frame_data(self, frame_number, timestamp):
        """Create error frame data structure"""
        return {
            "frame_metadata": {
                "frame_number": frame_number,
                "timestamp": timestamp,
                "error": "analysis_failed"
            },
            "face_detection": {
                "faces_detected": 0,
                "face_present": False,
                "multiple_people": False
            },
            "eye_gaze_analysis": {
                "eye_gaze_direction": "no_face_detected",
                "eyes_closed": False,
                "gaze_quality": "error"
            },
            "emotion_analysis": {
                "dominant_emotion": "neutral",
                "micro_expressions": ["unknown"],
                "emotion_stability": "unknown"
            },
            "posture_analysis": {
                "face_centering": "unknown",
                "posture_stability": "unknown"
            },
            "body_language": {
                "head_tilt": "unknown",
                "head_movement": "unknown"
            },
            "attention_focus": {
                "attention_level": "unknown",
                "looking_away": False,
                "distraction_present": True
            }
        }


# Combined Processor Class
class CombinedInterviewAnalyzer:
    def __init__(self, session_id, interview_id, user_id):
        self.session_id = session_id
        self.interview_id = interview_id
        self.user_id = user_id

        # Initialize analyzers
        self.frame_analyzer = AdvancedFrameAnalyzer()
        self.speech_analyzer = StreamlinedSpeechAnalyzer()

        # Processing counters
        self.frames_processed_count = 0
        self.frames_found_count = 0
        self.messages_scanned = 0
        self.session_messages_found = 0
        self.audio_files_processed = 0

        logger.info(f"🚀 Initialized CombinedInterviewAnalyzer")
        logger.info(f"   Session: {self.session_id}")
        logger.info(f"   Interview: {self.interview_id}")
        logger.info(f"   User: {self.user_id}")

    def process_complete_session(self):
        """Main processing function for complete session analysis"""
        logger.info(f"🎯 Starting COMBINED analysis for session: {self.session_id}")

        # Process frames from Kafka
        frame_analysis = self._process_video_frames()

        # Process audio from HDFS
        audio_analysis = self._process_audio_files()

        # Combine and correlate analyses
        combined_analysis = self._combine_analyses(frame_analysis, audio_analysis)

        # Generate final report
        return self._generate_combined_report(combined_analysis)

    def _process_video_frames(self):
        """Process video frames from Kafka"""
        logger.info(f"🎬 Processing video frames from Kafka...")

        try:
            self._scan_kafka_messages()

            if self.frames_found_count > 0:
                frame_analyses = self._process_session_frames()
                return {
                    "success": True,
                    "frame_analyses": frame_analyses,
                    "frames_processed": self.frames_processed_count,
                    "session_summary": self._generate_frame_session_summary(frame_analyses)
                }
            else:
                logger.warning(f"⚠️ No frame messages found for session {self.session_id}")
                return {"success": False, "error": "No frames found"}

        except Exception as e:
            logger.error(f"❌ Video frame processing failed: {e}")
            return {"success": False, "error": str(e)}

    def _process_audio_files(self):
        """Process audio files from HDFS"""
        logger.info(f"🎤 Processing audio files from HDFS...")

        try:
            # Get audio files from HDFS directory structure
            audio_dir = self._get_audio_directory_path()

            if not audio_dir or not os.path.exists(audio_dir):
                logger.warning(f"⚠️ Audio directory not found: {audio_dir}")
                return {"success": False, "error": "Audio directory not found"}

            # Analyze audio session
            audio_result = self.speech_analyzer.analyze_session_directory(audio_dir)

            if "error" in audio_result:
                return {"success": False, "error": audio_result["error"]}

            return {
                "success": True,
                "audio_analysis": audio_result,
                "audio_files_processed": len(audio_result.get("audio_analyses", []))
            }

        except Exception as e:
            logger.error(f"❌ Audio processing failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_audio_directory_path(self):
        """Get audio directory path - DIRECT HDFS access via REST API"""
        try:
            # Connect to database to get student info
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            query = """
            SELECT u.first_name, u.last_name, sp.student_id, i.attempt_number
            FROM interview_system_interview i
            JOIN user_management_customuser u ON i.student_id = u.id
            LEFT JOIN user_management_studentprofile sp ON u.id = sp.user_id
            WHERE i.id = %s
            """

            cursor.execute(query, (self.interview_id,))
            result = cursor.fetchone()

            if result:
                first_name, last_name, student_id, attempt_number = result
                
                # Construct directory name exactly as it appears in HDFS
                directory_name = f"{first_name}_{last_name}_{student_id}_attempt_{attempt_number}"
                
                # HDFS path
                hdfs_path = f"/student_audio_responses/{directory_name}"
                
                # Create local temp directory to store downloaded audio files
                local_temp_dir = f"/tmp/audio_temp_{self.session_id}_{attempt_number}"
                local_audio_dir = os.path.join(local_temp_dir, directory_name)
                os.makedirs(local_audio_dir, exist_ok=True)
                
                logger.info(f"Downloading audio files from HDFS: {hdfs_path}")
                logger.info(f"Local directory: {local_audio_dir}")
                
                try:
                    import requests
                    
                    # HDFS WebHDFS REST API endpoint - using namenode container
                    namenode_host = "namenode"
                    namenode_port = "9870"
                    
                    # List files in the HDFS directory
                    list_url = f"http://{namenode_host}:{namenode_port}/webhdfs/v1{hdfs_path}?op=LISTSTATUS"
                    
                    logger.info(f"Listing HDFS directory: {list_url}")
                    
                    response = requests.get(list_url, timeout=30)
                    if response.status_code == 200:
                        files_data = response.json()
                        files = files_data.get('FileStatuses', {}).get('FileStatus', [])
                        
                        audio_files_found = 0
                        
                        # Download each audio file
                        for file_info in files:
                            filename = file_info['pathSuffix']
                            if filename.endswith(('.webm', '.wav', '.mp3', '.m4a', '.flac')):
                                file_url = f"http://{namenode_host}:{namenode_port}/webhdfs/v1{hdfs_path}/{filename}?op=OPEN"
                                
                                logger.info(f"Downloading: {filename}")
                                
                                file_response = requests.get(file_url, timeout=120)
                                if file_response.status_code == 200:
                                    local_file_path = os.path.join(local_audio_dir, filename)
                                    with open(local_file_path, 'wb') as f:
                                        f.write(file_response.content)
                                    logger.info(f"Successfully downloaded: {filename} ({len(file_response.content)} bytes)")
                                    audio_files_found += 1
                                else:
                                    logger.error(f"Failed to download {filename}: HTTP {file_response.status_code}")
                        
                        if audio_files_found > 0:
                            logger.info(f"Downloaded {audio_files_found} audio files")
                            
                            # Convert .webm files to .wav for better compatibility
                            self._convert_webm_to_wav(local_audio_dir)
                            
                            cursor.close()
                            conn.close()
                            return local_audio_dir
                        else:
                            logger.error("No audio files found in HDFS directory")
                            
                    else:
                        logger.error(f"Failed to list HDFS directory: HTTP {response.status_code}")
                        logger.error(f"Response: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error accessing HDFS: {e}")
                except Exception as e:
                    logger.error(f"Error accessing HDFS via REST API: {e}")

            cursor.close()
            conn.close()
            return None

        except Exception as e:
            logger.error(f"Error getting audio directory path: {e}")
            return None

    def _convert_webm_to_wav(self, audio_dir):
        """Convert .webm files to .wav for better audio analysis compatibility"""
        try:
            import subprocess
            from pathlib import Path
            
            webm_files = list(Path(audio_dir).glob("*.webm"))
            
            if not webm_files:
                logger.info("No .webm files found to convert")
                return
                
            logger.info(f"Converting {len(webm_files)} .webm files to .wav")
            
            for webm_file in webm_files:
                wav_file = webm_file.with_suffix('.wav')
                
                # Use ffmpeg to convert webm to wav
                convert_cmd = [
                    "ffmpeg", "-i", str(webm_file), 
                    "-ar", "16000",  # 16kHz sample rate
                    "-ac", "1",      # Mono channel
                    "-y",            # Overwrite output
                    str(wav_file)
                ]
                
                try:
                    result = subprocess.run(
                        convert_cmd, 
                        capture_output=True, 
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Converted: {webm_file.name} -> {wav_file.name}")
                    else:
                        logger.warning(f"Failed to convert {webm_file.name}: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.error(f"Conversion timeout for {webm_file.name}")
                except Exception as e:
                    logger.error(f"Conversion error for {webm_file.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in webm to wav conversion: {e}")
            
    def _scan_kafka_messages(self):
        """Scan Kafka messages for session frames"""
        try:
            logger.info(f"📡 Scanning Kafka for session: {self.session_id}")

            kafka_config = KAFKA_CONFIG.copy()
            kafka_config['group_id'] = None

            consumer = KafkaConsumer(**kafka_config)
            partition = TopicPartition(KAFKA_TOPIC, 0)
            consumer.assign([partition])
            consumer.seek_to_beginning(partition)

            scan_start_time = time.time()
            max_scan_time = 300  # 5 minutes

            for message_batch in consumer:
                print("🔥 RAW RECORD OBJECT:", message_batch)
                print("🔥 RAW VALUE:", message_batch.value)
                print("🔥 VALUE TYPE:", type(message_batch.value))
                if time.time() - scan_start_time > max_scan_time:
                    logger.warning(f"⏰ Kafka scan timeout after {max_scan_time}s")
                    break

                try:
                    self.messages_scanned += 1
                    message_data = message_batch.value

                    msg_session_id = message_data.get('session_id')
                    msg_type = message_data.get('type', '')

                    if msg_session_id == self.session_id:
                        self.session_messages_found += 1

                        if msg_type == 'frame':
                            self.frames_found_count += 1
                            self._store_frame_message(message_data)

                    if self.messages_scanned % 100 == 0:
                        logger.info(f"📊 Scanned {self.messages_scanned} messages, frames found: {self.frames_found_count}")

                except Exception as e:
                    logger.error(f"❌ Error processing message {self.messages_scanned}: {e}")
                    continue

            consumer.close()
            logger.info(f"✅ Kafka scan completed - {self.frames_found_count} frames found")

        except Exception as e:
            logger.error(f"❌ Kafka scanning failed: {e}")

    def _store_frame_message(self, message_data):
        """Store frame message for processing"""
        try:
            frames_dir = f"/tmp/frames_{self.session_id}"
            os.makedirs(frames_dir, exist_ok=True)

            frame_file = os.path.join(frames_dir, f"frame_{self.frames_found_count}.json")
            with open(frame_file, 'w') as f:
                json.dump(message_data, f)

        except Exception as e:
            logger.error(f"❌ Error storing frame message: {e}")

    def _process_session_frames(self):
        """Process all stored frame messages"""
        try:
            frames_dir = f"/tmp/frames_{self.session_id}"
            frame_files = sorted([f for f in os.listdir(frames_dir) if f.startswith('frame_')])

            logger.info(f"🎬 Processing {len(frame_files)} frames")

            frame_analyses = []

            for i, frame_file in enumerate(frame_files):
                try:
                    frame_path = os.path.join(frames_dir, frame_file)
                    with open(frame_path, 'r') as f:
                        message_data = json.load(f)

                    frame_analysis = self._process_single_frame_message(message_data, i + 1)
                    if frame_analysis:
                        frame_analyses.append(frame_analysis)
                        self.frames_processed_count += 1

                except Exception as e:
                    logger.error(f"❌ Error processing frame file {frame_file}: {e}")

            # Cleanup
            try:
                import shutil
                shutil.rmtree(frames_dir)
            except:
                pass

            return frame_analyses

        except Exception as e:
            logger.error(f"❌ Error in frame processing: {e}")
            return []

    def _process_single_frame_message(self, message_dict, frame_number):
        """Process a single frame message"""
        try:
            # Extract frame data
            frame_b64 = self._extract_frame_data(message_dict)
            if not frame_b64:
                return None

            # Decode frame
            try:
                frame_bytes = base64.b64decode(frame_b64)
                frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                if frame is None or frame.shape[0] < 100 or frame.shape[1] < 100:
                    return None

            except Exception as e:
                logger.error(f"❌ Frame decoding error: {e}")
                return None

            # Perform analysis
            timestamp = message_dict.get('timestamp', time.time())
            analysis_result = self.frame_analyzer.analyze_frame_comprehensive(frame, frame_number, timestamp)

            return analysis_result

        except Exception as e:
            logger.error(f"❌ Error in single frame processing: {e}")
            return None

    def _extract_frame_data(self, message_dict):
        """Extract frame data from message"""
        frame_b64 = None

        if 'frame_data' in message_dict:
            frame_data_obj = message_dict['frame_data']
            if isinstance(frame_data_obj, dict):
                frame_b64 = frame_data_obj.get('frame_data')
            elif isinstance(frame_data_obj, str):
                frame_b64 = frame_data_obj

        if not frame_b64:
            for key in ['data', 'image_data', 'frame', 'base64_data']:
                if key in message_dict:
                    frame_b64 = message_dict[key]
                    break

        return frame_b64 if isinstance(frame_b64, str) and len(frame_b64) > 2000 else None

    def _generate_frame_session_summary(self, frame_analyses):
        """Generate frame session summary"""
        if not frame_analyses:
            return {"error": "No frame analyses available"}

        try:
            total_frames = len(frame_analyses)

            # Eye contact statistics
            looking_at_camera_frames = sum(1 for f in frame_analyses
                                         if f.get('eye_gaze_analysis', {}).get('eye_gaze_direction') == 'looking_at_camera')
            eye_contact_percentage = (looking_at_camera_frames / total_frames) * 100

            # Attention statistics
            attention_levels = [f.get('attention_focus', {}).get('attention_level', 'unknown')
                              for f in frame_analyses]
            focused_frames = sum(1 for level in attention_levels if level == 'focused')
            focus_percentage = (focused_frames / total_frames) * 100

            # Emotion analysis
            emotions = [f.get('emotion_analysis', {}).get('dominant_emotion', 'neutral')
                       for f in frame_analyses]
            emotion_distribution = {emotion: emotions.count(emotion) for emotion in set(emotions)}

            return {
                'total_frames_analyzed': total_frames,
                'eye_contact_percentage': round(eye_contact_percentage, 2),
                'focus_percentage': round(focus_percentage, 2),
                'emotion_distribution': emotion_distribution,
                'dominant_emotion': max(emotion_distribution, key=emotion_distribution.get) if emotion_distribution else 'neutral'
            }

        except Exception as e:
            logger.error(f"❌ Frame session summary generation error: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}

    def _combine_analyses(self, frame_analysis, audio_analysis):
        """Combine frame and audio analyses with correlation"""
        try:
            combined = {
                "video_analysis": frame_analysis,
                "audio_analysis": audio_analysis,
                "correlation_analysis": {}
            }

            # Only proceed with correlation if both analyses succeeded
            if frame_analysis.get("success") and audio_analysis.get("success"):
                combined["correlation_analysis"] = self._correlate_video_audio(
                    frame_analysis, audio_analysis
                )

            return combined

        except Exception as e:
            logger.error(f"❌ Error combining analyses: {e}")
            return {
                "video_analysis": frame_analysis,
                "audio_analysis": audio_analysis,
                "correlation_analysis": {"error": str(e)}
            }

    def _assess_audio_confidence(self, audio_summary):
        """Assess confidence from audio cues"""
        try:
            overall_clarity = audio_summary.get("overall_clarity", "poor")
            overall_pace = audio_summary.get("overall_pace", "normal")
            speaking_ratio = audio_summary.get("aggregated_metrics", {}).get("speaking_duration", 0)
            total_duration = audio_summary.get("aggregated_metrics", {}).get("total_duration", 1)

            # Calculate speaking ratio
            speaking_ratio_pct = (speaking_ratio / max(total_duration, 1)) * 100

            # Score based on clarity, pace, and speaking activity
            clarity_score = {"good": 0.8, "fair": 0.5, "poor": 0.2}.get(overall_clarity, 0.2)
            pace_score = {"normal": 0.8, "slow": 0.6, "fast": 0.6}.get(overall_pace, 0.6)
            activity_score = min(1.0, speaking_ratio_pct / 50)  # Normalize

            confidence_score = (clarity_score + pace_score + activity_score) / 3

            if confidence_score > 0.7:
                return {"level": "high", "score": confidence_score}
            elif confidence_score > 0.4:
                return {"level": "moderate", "score": confidence_score}
            else:
                return {"level": "low", "score": confidence_score}
        except Exception as e:  # ← This line needs to be unindented by 4 spaces
            return {"level": "unknown", "score": 0, "error": str(e)}

    def _correlate_video_audio(self, frame_analysis, audio_analysis):
        """Correlate video and audio analysis results"""
        try:
            correlation = {}

            # Get frame summary
            frame_summary = frame_analysis.get("session_summary", {})

            # Get audio summary
            audio_summary = audio_analysis.get("audio_analysis", {}).get("session_summary", {})

            # Cross-modal confidence assessment
            visual_confidence = self._assess_visual_confidence(frame_summary)
            audio_confidence = self._assess_audio_confidence(audio_summary)

            correlation["confidence_correlation"] = {
                "visual_confidence": visual_confidence,
                "audio_confidence": audio_confidence,
                "confidence_alignment": self._compare_confidence_levels(visual_confidence, audio_confidence)
            }

            # Engagement correlation
            visual_engagement = self._assess_visual_engagement(frame_summary)
            audio_engagement = self._assess_audio_engagement(audio_summary)

            correlation["engagement_correlation"] = {
                "visual_engagement": visual_engagement,
                "audio_engagement": audio_engagement,
                "engagement_alignment": self._compare_engagement_levels(visual_engagement, audio_engagement)
            }

            # Overall correlation score
            correlation["overall_correlation"] = self._calculate_overall_correlation(
                correlation["confidence_correlation"],
                correlation["engagement_correlation"]
            )

            return correlation

        except Exception as e:
            logger.error(f"❌ Error in video-audio correlation: {e}")
            return {"error": str(e)}

    def _assess_visual_confidence(self, frame_summary):
        """Assess confidence from visual cues"""
        try:
            eye_contact_pct = frame_summary.get("eye_contact_percentage", 0)
            focus_pct = frame_summary.get("focus_percentage", 0)

            # Simple confidence scoring based on eye contact and focus
            confidence_score = (eye_contact_pct + focus_pct) / 200  # Normalize to 0-1

            if confidence_score > 0.7:
                return {"level": "high", "score": confidence_score}
            elif confidence_score > 0.4:
                return {"level": "moderate", "score": confidence_score}
            else:
                return {"level": "low", "score": confidence_score}

        except Exception as e:
            return {"level": "unknown", "score": 0, "error": str(e)}

    def _assess_visual_engagement(self, frame_summary):
        """Assess engagement from visual cues"""
        try:
            focus_pct = frame_summary.get("focus_percentage", 0)
            dominant_emotion = frame_summary.get("dominant_emotion", "neutral")

            # Base engagement on focus and positive emotions
            emotion_boost = 0.2 if dominant_emotion in ["happiness", "surprise"] else 0
            engagement_score = (focus_pct / 100) + emotion_boost
            engagement_score = min(1.0, engagement_score)

            if engagement_score > 0.7:
                return {"level": "high", "score": engagement_score}
            elif engagement_score > 0.4:
                return {"level": "moderate", "score": engagement_score}
            else:
                return {"level": "low", "score": engagement_score}

        except Exception as e:
            return {"level": "unknown", "score": 0, "error": str(e)}

    def _assess_audio_engagement(self, audio_summary):
        """Assess engagement from audio cues"""
        try:
            speaking_files = audio_summary.get("aggregated_metrics", {}).get("speaking_files", 0)
            total_files = audio_summary.get("aggregated_metrics", {}).get("total_audio_files", 1)

            # Engagement based on proportion of files with speech activity
            engagement_score = speaking_files / max(total_files, 1)

            if engagement_score > 0.8:
                return {"level": "high", "score": engagement_score}
            elif engagement_score > 0.5:
                return {"level": "moderate", "score": engagement_score}
            else:
                return {"level": "low", "score": engagement_score}

        except Exception as e:
            return {"level": "unknown", "score": 0, "error": str(e)}

    def _compare_confidence_levels(self, visual_conf, audio_conf):
        """Compare confidence levels between visual and audio"""
        try:
            visual_level = visual_conf.get("level", "unknown")
            audio_level = audio_conf.get("level", "unknown")

            if visual_level == audio_level:
                return {"alignment": "strong", "description": f"Both visual and audio indicate {visual_level} confidence"}
            elif (visual_level == "high" and audio_level == "moderate") or (visual_level == "moderate" and audio_level == "high"):
                return {"alignment": "moderate", "description": "Visual and audio confidence levels are close"}
            else:
                return {"alignment": "weak", "description": f"Visual ({visual_level}) and audio ({audio_level}) confidence levels differ significantly"}

        except Exception as e:
            return {"alignment": "unknown", "description": f"Error comparing confidence: {str(e)}"}

    def _compare_engagement_levels(self, visual_eng, audio_eng):
        """Compare engagement levels between visual and audio"""
        try:
            visual_level = visual_eng.get("level", "unknown")
            audio_level = audio_eng.get("level", "unknown")

            if visual_level == audio_level:
                return {"alignment": "strong", "description": f"Both visual and audio indicate {visual_level} engagement"}
            elif (visual_level == "high" and audio_level == "moderate") or (visual_level == "moderate" and audio_level == "high"):
                return {"alignment": "moderate", "description": "Visual and audio engagement levels are close"}
            else:
                return {"alignment": "weak", "description": f"Visual ({visual_level}) and audio ({audio_level}) engagement levels differ significantly"}

        except Exception as e:
            return {"alignment": "unknown", "description": f"Error comparing engagement: {str(e)}"}

    def _calculate_overall_correlation(self, confidence_corr, engagement_corr):
        """Calculate overall correlation score"""
        try:
            conf_alignment = confidence_corr.get("confidence_alignment", {}).get("alignment", "weak")
            eng_alignment = engagement_corr.get("engagement_alignment", {}).get("alignment", "weak")

            # Score alignments
            alignment_scores = {"strong": 1.0, "moderate": 0.6, "weak": 0.2, "unknown": 0}
            conf_score = alignment_scores.get(conf_alignment, 0)
            eng_score = alignment_scores.get(eng_alignment, 0)

            overall_score = (conf_score + eng_score) / 2

            if overall_score > 0.8:
                correlation_level = "excellent"
            elif overall_score > 0.6:
                correlation_level = "good"
            elif overall_score > 0.4:
                correlation_level = "moderate"
            else:
                correlation_level = "poor"

            return {
                "correlation_score": overall_score,
                "correlation_level": correlation_level,
                "description": f"Overall correlation between visual and audio analysis is {correlation_level}"
            }

        except Exception as e:
            return {
                "correlation_score": 0,
                "correlation_level": "unknown",
                "description": f"Error calculating correlation: {str(e)}"
            }

    def _generate_combined_report(self, combined_analysis):
        """Generate final combined report"""
        try:
            logger.info(f"📊 Generating combined analysis report for session: {self.session_id}")

            # Create comprehensive report
            timestamp = int(time.time())
            hash_part = self.session_id.split('_')[-1] if '_' in self.session_id else 'nohash'
            output_filename = f"COMBINED_analysis_{self.user_id}_{self.interview_id}_{timestamp}_{hash_part}.json"
            output_path = f"/app/{output_filename}"

            comprehensive_report = {
                'metadata': {
                    'session_id': self.session_id,
                    'user_id': self.user_id,
                    'interview_id': self.interview_id,
                    'timestamp': timestamp,
                    'analysis_type': 'combined_video_audio_analysis',
                    'filename': output_filename,
                    'processing_stats': {
                        'frames_processed': self.frames_processed_count,
                        'frames_found': self.frames_found_count,
                        'audio_files_processed': self.audio_files_processed,
                        'messages_scanned': self.messages_scanned,
                        'session_messages_found': self.session_messages_found
                    },
                    'capabilities': {
                        'advanced_video_analysis': ADVANCED_LIBS_AVAILABLE,
                        'speech_analysis_librosa': HAS_LIBROSA,
                        'speech_analysis_opensmile': HAS_OPENSMILE,
                        'speech_analysis_praat': HAS_PRAAT,
                        'correlation_analysis': True
                    }
                },
                'video_analysis': combined_analysis.get('video_analysis', {}),
                'audio_analysis': combined_analysis.get('audio_analysis', {}),
                'cross_modal_correlation': combined_analysis.get('correlation_analysis', {}),
                'integrated_assessment': self._generate_integrated_assessment(combined_analysis),
                'recommendations': self._generate_recommendations(combined_analysis)
            }

            with open(output_path, 'w') as f:
                json.dump(comprehensive_report, f, indent=4, default=str)

            logger.info(f"✅ Combined analysis report saved to: {output_path}")
            logger.info(f"📁 Filename: {output_filename}")
            logger.info(f"📊 Final Processing Summary:")
            logger.info(f"   • Frames processed: {self.frames_processed_count}")
            logger.info(f"   • Audio files processed: {self.audio_files_processed}")
            logger.info(f"   • Video analysis: {'✅' if combined_analysis.get('video_analysis', {}).get('success') else '❌'}")
            logger.info(f"   • Audio analysis: {'✅' if combined_analysis.get('audio_analysis', {}).get('success') else '❌'}")
            logger.info(f"   • Cross-modal correlation: {'✅' if 'error' not in combined_analysis.get('correlation_analysis', {}) else '❌'}")

            return comprehensive_report

        except Exception as e:
            logger.error(f"❌ Combined analysis report generation failed: {e}")
            return {"error": str(e)}

    def _generate_integrated_assessment(self, combined_analysis):
        """Generate integrated assessment combining video and audio insights"""
        try:
            integrated = {
                "overall_performance": "unknown",
                "key_strengths": [],
                "improvement_areas": [],
                "behavioral_insights": {},
                "interview_readiness": "unknown"
            }

            video_success = combined_analysis.get('video_analysis', {}).get('success', False)
            audio_success = combined_analysis.get('audio_analysis', {}).get('success', False)
            correlation = combined_analysis.get('correlation_analysis', {})

            if video_success and audio_success:
                # Both analyses successful - full integrated assessment

                # Get key metrics
                video_summary = combined_analysis['video_analysis'].get('session_summary', {})
                audio_summary = combined_analysis['audio_analysis']['audio_analysis'].get('session_summary', {})

                # Overall performance assessment
                visual_engagement = video_summary.get('focus_percentage', 0)
                audio_clarity = {"good": 80, "fair": 60, "poor": 40}.get(audio_summary.get('overall_clarity', 'poor'), 40)
                eye_contact = video_summary.get('eye_contact_percentage', 0)

                performance_score = (visual_engagement + audio_clarity + eye_contact) / 3

                if performance_score > 70:
                    integrated["overall_performance"] = "excellent"
                elif performance_score > 60:
                    integrated["overall_performance"] = "good"
                elif performance_score > 45:
                    integrated["overall_performance"] = "fair"
                else:
                    integrated["overall_performance"] = "needs_improvement"

                # Key strengths
                if eye_contact > 70:
                    integrated["key_strengths"].append("strong_eye_contact")
                if audio_summary.get('overall_clarity') == 'good':
                    integrated["key_strengths"].append("clear_communication")
                if visual_engagement > 70:
                    integrated["key_strengths"].append("high_visual_engagement")
                if correlation.get('overall_correlation', {}).get('correlation_level') in ['excellent', 'good']:
                    integrated["key_strengths"].append("consistent_behavioral_signals")

                # Improvement areas
                if eye_contact < 50:
                    integrated["improvement_areas"].append("improve_eye_contact")
                if audio_summary.get('overall_clarity') == 'poor':
                    integrated["improvement_areas"].append("enhance_speech_clarity")
                if visual_engagement < 50:
                    integrated["improvement_areas"].append("increase_attention_focus")
                if correlation.get('overall_correlation', {}).get('correlation_level') == 'poor':
                    integrated["improvement_areas"].append("align_verbal_nonverbal_communication")

                # Behavioral insights
                dominant_emotion = video_summary.get('dominant_emotion', 'neutral')
                confidence_alignment = correlation.get('confidence_correlation', {}).get('confidence_alignment', {}).get('alignment', 'unknown')

                integrated["behavioral_insights"] = {
                    "dominant_emotion": dominant_emotion,
                    "confidence_consistency": confidence_alignment,
                    "communication_style": "balanced" if confidence_alignment == "strong" else "inconsistent",
                    "stress_indicators": self._assess_stress_indicators(video_summary, audio_summary)
                }

                # Interview readiness
                if performance_score > 65 and len(integrated["improvement_areas"]) <= 2:
                    integrated["interview_readiness"] = "ready"
                elif performance_score > 50:
                    integrated["interview_readiness"] = "mostly_ready"
                else:
                    integrated["interview_readiness"] = "needs_preparation"

            elif video_success:
                # Only video analysis available
                integrated = self._video_only_assessment(combined_analysis['video_analysis'])
            elif audio_success:
                # Only audio analysis available
                integrated = self._audio_only_assessment(combined_analysis['audio_analysis'])

            return integrated

        except Exception as e:
            logger.error(f"❌ Integrated assessment generation error: {e}")
            return {"error": str(e)}

    def _assess_stress_indicators(self, video_summary, audio_summary):
        """Assess stress indicators from both modalities"""
        stress_indicators = []

        # Video stress indicators
        if video_summary.get('dominant_emotion') in ['anger', 'fear', 'sadness']:
            stress_indicators.append("negative_emotional_expression")

        # Audio stress indicators
        if audio_summary.get('overall_pace') == 'fast':
            stress_indicators.append("rapid_speech")
        elif audio_summary.get('overall_pace') == 'slow':
            stress_indicators.append("hesitant_speech")

        if audio_summary.get('overall_clarity') == 'poor':
            stress_indicators.append("voice_quality_issues")

        return stress_indicators if stress_indicators else ["minimal_stress_detected"]

    def _video_only_assessment(self, video_analysis):
        """Generate assessment based only on video analysis"""
        try:
            video_summary = video_analysis.get('session_summary', {})

            return {
                "overall_performance": "partial_assessment_video_only",
                "key_strengths": ["visual_analysis_available"],
                "improvement_areas": ["audio_analysis_needed"],
                "behavioral_insights": {
                    "dominant_emotion": video_summary.get('dominant_emotion', 'unknown'),
                    "eye_contact_quality": "good" if video_summary.get('eye_contact_percentage', 0) > 60 else "needs_improvement",
                    "visual_engagement": "high" if video_summary.get('focus_percentage', 0) > 60 else "moderate"
                },
                "interview_readiness": "partial_assessment"
            }
        except:
            return {"error": "Video-only assessment failed"}

    def _audio_only_assessment(self, audio_analysis):
        """Generate assessment based only on audio analysis"""
        try:
            audio_summary = audio_analysis.get('audio_analysis', {}).get('session_summary', {})

            return {
                "overall_performance": "partial_assessment_audio_only",
                "key_strengths": ["audio_analysis_available"],
                "improvement_areas": ["video_analysis_needed"],
                "behavioral_insights": {
                    "speech_clarity": audio_summary.get('overall_clarity', 'unknown'),
                    "speaking_pace": audio_summary.get('overall_pace', 'unknown'),
                    "verbal_engagement": "high" if audio_summary.get('overall_speaking') else "low"
                },
                "interview_readiness": "partial_assessment"
            }
        except:
            return {"error": "Audio-only assessment failed"}

    def _generate_recommendations(self, combined_analysis):
        """Generate actionable recommendations"""
        try:
            recommendations = {
                "immediate_actions": [],
                "practice_suggestions": [],
                "technical_improvements": [],
                "long_term_development": []
            }

            video_success = combined_analysis.get('video_analysis', {}).get('success', False)
            audio_success = combined_analysis.get('audio_analysis', {}).get('success', False)

            if video_success and audio_success:
                # Full recommendations
                video_summary = combined_analysis['video_analysis'].get('session_summary', {})
                audio_summary = combined_analysis['audio_analysis']['audio_analysis'].get('session_summary', {})
                correlation = combined_analysis.get('correlation_analysis', {})

                # Eye contact recommendations
                if video_summary.get('eye_contact_percentage', 0) < 50:
                    recommendations["immediate_actions"].append("Practice maintaining eye contact with camera")
                    recommendations["practice_suggestions"].append("Record practice sessions focusing on camera engagement")

                # Speech clarity recommendations
                if audio_summary.get('overall_clarity') == 'poor':
                    recommendations["immediate_actions"].append("Speak more slowly and clearly")
                    recommendations["practice_suggestions"].append("Practice articulation exercises")

                # Pace recommendations
                if audio_summary.get('overall_pace') == 'fast':
                    recommendations["immediate_actions"].append("Take pauses between sentences")
                elif audio_summary.get('overall_pace') == 'slow':
                    recommendations["immediate_actions"].append("Increase speaking confidence and pace")

                # Correlation recommendations
                correlation_level = correlation.get('overall_correlation', {}).get('correlation_level', 'unknown')
                if correlation_level in ['poor', 'moderate']:
                    recommendations["practice_suggestions"].append("Practice aligning verbal confidence with body language")
                    recommendations["long_term_development"].append("Work on consistent communication across all modalities")

                # Technical improvements
                recommendations["technical_improvements"].extend([
                    "Ensure good lighting for video analysis",
                    "Use external microphone for clearer audio",
                    "Maintain stable internet connection"
                ])

            return recommendations

        except Exception as e:
            logger.error(f"❌ Recommendations generation error: {e}")
            return {"error": str(e)}


def install_dependencies():
    """Install required dependencies in the dlib container"""
    try:
        logger.info("🔧 Installing required dependencies...")

        # Install Python packages
        packages = [
            "librosa",
            "soundfile",
            "opensmile",
            "praat-parselmouth",
            "scipy",
            "scikit-learn",
            "kafka-python",
            "mysql-connector-python"
        ]

        for package in packages:
            try:
                subprocess.run([
                    "pip", "install", package
                ], check=True, capture_output=True)
                logger.info(f"✅ Installed {package}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"⚠️ Failed to install {package}: {e}")

        # Install system dependencies if needed
        try:
            subprocess.run([
                "apt-get", "update"
            ], check=True, capture_output=True)

            subprocess.run([
                "apt-get", "install", "-y", "ffmpeg", "libsndfile1"
            ], check=True, capture_output=True)

            logger.info("✅ System dependencies installed")
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ System dependencies installation failed: {e}")

        logger.info("🎉 Dependencies installation completed")
        return True

    except Exception as e:
        logger.error(f"❌ Dependencies installation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Combined Video and Audio Interview Analyzer")
    parser.add_argument('--session_id', required=True, help='Session ID for the interview')
    parser.add_argument('--interview_id', required=True, type=int, help='Interview ID')
    parser.add_argument('--user_id', required=True, help='User ID')
    parser.add_argument('--install_deps', action='store_true', help='Install dependencies first')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🚀 Starting COMBINED Video and Audio Interview Analysis")
    logger.info(f"   Session ID: {args.session_id}")
    logger.info(f"   Interview ID: {args.interview_id}")
    logger.info(f"   User ID: {args.user_id}")

    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            logger.error("❌ Dependency installation failed")
            sys.exit(1)

    if args.auto_process:
        try:
            processor = CombinedInterviewAnalyzer(
                session_id=args.session_id,
                interview_id=args.interview_id,
                user_id=args.user_id
            )

            result = processor.process_complete_session()

            if result and "error" not in result:
                logger.info(f"🎉 Combined analysis completed successfully!")
                logger.info(f"📊 Video frames processed: {processor.frames_processed_count}")
                logger.info(f"🎤 Audio files processed: {processor.audio_files_processed}")
                logger.info(f"✨ Cross-modal correlation analysis: ✅")
                logger.info(f"📄 Integrated assessment: ✅")
                logger.info(f"💡 Actionable recommendations: ✅")
                sys.exit(0)
            else:
                logger.error(f"💥 Combined analysis failed!")
                if result:
                    logger.error(f"Error: {result.get('error', 'Unknown error')}")
                sys.exit(1)

        except Exception as e:
            logger.error(f"❌ Fatal error in combined processing: {e}")
            sys.exit(1)
    else:
        logger.info(f"ℹ️ Use --auto_process to start analysis")
        logger.info(f"📋 Combined Analysis Features:")
        logger.info(f"   • Video frame analysis from Kafka")
        logger.info(f"   • Audio speech analysis from HDFS")
        logger.info(f"   • Cross-modal correlation analysis")
        logger.info(f"   • Integrated behavioral assessment")
        logger.info(f"   • Actionable recommendations")
        logger.info(f"   • Complete JSON output for further processing")

if __name__ == "__main__":
    main()

