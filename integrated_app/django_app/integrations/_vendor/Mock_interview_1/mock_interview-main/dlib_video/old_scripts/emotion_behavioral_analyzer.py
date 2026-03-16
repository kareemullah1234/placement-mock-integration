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

# Enhanced libraries for better analysis
try:
    import dlib
    import mediapipe as mp
    from scipy.spatial.distance import euclidean
    from sklearn.preprocessing import StandardScaler
    ADVANCED_LIBS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Advanced libraries not available: {e}")
    ADVANCED_LIBS_AVAILABLE = False

# Enhanced Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/enhanced_video_analysis.log')
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
    'bootstrap_servers': ['kafka-frames:9092'],
    'auto_offset_reset': 'earliest',
    'consumer_timeout_ms': 150000,
    'group_id': None,
    'value_deserializer': lambda v: json.loads(v.decode('utf-8', 'ignore')),
    'enable_auto_commit': False,
    'max_poll_records': 100
}

class AdvancedFrameAnalyzer:
    def __init__(self):
        self.face_detector = None
        self.landmark_predictor = None
        self.mp_face_mesh = None
        self.mp_drawing = None
        self.emotion_history = deque(maxlen=30)  # Last 30 frames for micro-expressions
        self.gaze_history = deque(maxlen=20)    # Last 20 frames for focus consistency
        self.confidence_metrics = deque(maxlen=50)  # For confidence scoring
        self.head_tilt_history = deque(maxlen=15)   # For head movement tracking
        
        if ADVANCED_LIBS_AVAILABLE:
            self._initialize_advanced_models()
    
    def _initialize_advanced_models(self):
        """Initialize dlib and MediaPipe models"""
        try:
            # Initialize dlib face detector and landmark predictor
            self.face_detector = dlib.get_frontal_face_detector()
            
            # Try multiple paths for the predictor file
            predictor_paths = [
                "/app/open_cv/shape_predictor_68_face_landmarks.dat",  # Your actual location
                "/tmp/shape_predictor_68_face_landmarks.dat",
                "/app/models/shape_predictor_68_face_landmarks.dat",
                "./shape_predictor_68_face_landmarks.dat",
                "/usr/local/share/dlib/shape_predictor_68_face_landmarks.dat"
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
                logger.warning("⚠️ Dlib landmark predictor not found in any location")
                logger.info("💡 To download: wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2 -O /tmp/shape_predictor_68_face_landmarks.dat.bz2 && bunzip2 /tmp/shape_predictor_68_face_landmarks.dat.bz2")
                logger.info("🔄 Falling back to MediaPipe-only analysis")
            
            # Initialize MediaPipe (this can work independently of dlib)
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
        """Comprehensive frame analysis with cleaned-up output structure"""
        try:
            # Initialize analysis structure
            analysis = {
                "frame_metadata": {
                    "frame_number": frame_number,
                    "timestamp": timestamp
                }
            }
            
            # Basic face detection
            face_data = self._detect_faces(frame)
            analysis["face_detection"] = face_data
            
            if face_data["face_present"]:
                # Eye gaze analysis (cleaned up)
                analysis["eye_gaze_analysis"] = self._analyze_eye_gaze_clean(frame)
                
                # Enhanced emotion analysis with micro-expressions (cleaned up)
                analysis["emotion_analysis"] = self._analyze_emotions_clean(frame)
                
                # Posture analysis (cleaned up)
                analysis["posture_analysis"] = self._analyze_posture_clean(frame)
                
                # Body language analysis
                analysis["body_language"] = self._analyze_body_language_clean(frame)
                
                # Engagement and confidence metrics
                analysis["engagement_metrics"] = self._calculate_engagement_metrics_clean(analysis)
                analysis["confidence_indicators"] = self._calculate_confidence_indicators_clean(analysis)
                
                # Distraction analysis
                analysis["distraction_analysis"] = self._analyze_distractions_clean(analysis)
                
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive frame analysis: {e}")
            return self._create_error_frame_data(frame_number, timestamp)

    def _detect_faces(self, frame):
        """Enhanced face detection with size and positioning metrics"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if ADVANCED_LIBS_AVAILABLE and self.face_detector:
                faces = self.face_detector(gray)
                faces_detected = len(faces)
            else:
                # Fallback to OpenCV Haar cascades
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

    def _analyze_eye_gaze_clean(self, frame):
        """Cleaned-up eye gaze analysis using dlib landmarks"""
        try:
            if not ADVANCED_LIBS_AVAILABLE or not self.landmark_predictor:
                return self._basic_gaze_analysis_clean(frame)
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_detector(gray)
            
            if len(faces) == 0:
                return {
                    "eye_gaze_direction": "no_face", 
                    "eyes_closed": False,
                    "eye_contact_confidence": 0.0,
                    "gaze_quality": "no_face"
                }
            
            # Get landmarks for the first face
            landmarks = self.landmark_predictor(gray, faces[0])
            
            # Eye region landmarks
            left_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)]
            right_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)]
            
            # Calculate eye aspect ratio for blink detection
            ear_left = self._calculate_eye_aspect_ratio(left_eye_points)
            ear_right = self._calculate_eye_aspect_ratio(right_eye_points)
            avg_ear = (ear_left + ear_right) / 2.0
            
            # Determine if eyes are closed
            eyes_closed = avg_ear < 0.2
            
            # Estimate gaze direction based on eye center relative to face center
            face_center_x = (faces[0].left() + faces[0].right()) // 2
            left_eye_center = np.mean(left_eye_points, axis=0)
            right_eye_center = np.mean(right_eye_points, axis=0)
            eye_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
            
            # Calculate gaze direction and confidence
            gaze_offset = abs(eye_center_x - face_center_x)
            max_offset = faces[0].width() * 0.15
            
            if eyes_closed:
                gaze_direction = "eyes_closed"
                confidence = 0.9
            elif gaze_offset < max_offset * 0.5:
                gaze_direction = "looking_at_camera"
                confidence = max(0.3, 1.0 - (gaze_offset / max_offset))
            elif eye_center_x < face_center_x - max_offset:
                gaze_direction = "looking_left"
                confidence = min(0.9, gaze_offset / max_offset)
            elif eye_center_x > face_center_x + max_offset:
                gaze_direction = "looking_right" 
                confidence = min(0.9, gaze_offset / max_offset)
            else:
                gaze_direction = "gaze_averted"
                confidence = min(0.8, gaze_offset / max_offset)
            
            # Update gaze history for consistency tracking
            is_looking_at_camera = gaze_direction == "looking_at_camera"
            self.gaze_history.append(is_looking_at_camera)
            
            return {
                "eye_gaze_direction": gaze_direction,
                "eyes_closed": eyes_closed,
                "eye_contact_confidence": round(confidence, 3),
                "gaze_quality": self._classify_gaze_quality(confidence)
            }
            
        except Exception as e:
            logger.error(f"❌ Eye gaze analysis error: {e}")
            return self._basic_gaze_analysis_clean(frame)

    def _calculate_eye_aspect_ratio(self, eye_points):
        """Calculate Eye Aspect Ratio for blink detection"""
        try:
            # Vertical eye landmarks
            A = euclidean(eye_points[1], eye_points[5])
            B = euclidean(eye_points[2], eye_points[4])
            # Horizontal eye landmark
            C = euclidean(eye_points[0], eye_points[3])
            # EAR formula
            ear = (A + B) / (2.0 * C)
            return ear
        except:
            return 0.25  # Default EAR

    def _analyze_emotions_clean(self, frame):
        """Enhanced emotion analysis with micro-expressions - cleaned up"""
        try:
            # Basic emotion detection (integrate with emotion detection library like FER)
            # For now using placeholder logic - replace with actual emotion detection
            dominant_emotion = self._detect_primary_emotion(frame)
            emotion_intensity = self._calculate_emotion_intensity(frame)
            emotion_confidence = self._calculate_emotion_confidence(frame)
            
            # Micro-expression detection
            micro_expressions = self._detect_micro_expressions_advanced(frame, dominant_emotion)
            
            # Calculate emotion variability from history
            self.emotion_history.append(dominant_emotion)
            emotion_variability = self._calculate_emotion_variability()
            
            return {
                "dominant_emotion": dominant_emotion,
                "emotion_intensity": round(emotion_intensity, 2),
                "emotion_confidence": round(emotion_confidence, 2),
                "micro_expressions": micro_expressions,
                "emotion_variability": emotion_variability
            }
            
        except Exception as e:
            logger.error(f"❌ Emotion analysis error: {e}")
            return {
                "dominant_emotion": "neutral",
                "emotion_intensity": 0.5,
                "emotion_confidence": 0.5,
                "micro_expressions": ["neutral"],
                "emotion_variability": "unknown"
            }

    def _detect_primary_emotion(self, frame):
        """Detect primary emotion using available cascades"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Try to use the smile cascade from your directory first
            smile_cascade_paths = [
                "/app/open_cv/haarcascade_smile.xml",  # Your actual location
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
                    return "positive"
            
            # Fallback emotion detection using basic facial features
            # You can enhance this with more sophisticated emotion detection
            return "neutral"
            
        except Exception as e:
            logger.error(f"❌ Primary emotion detection error: {e}")
            return "neutral"

    def _calculate_emotion_intensity(self, frame):
        """Calculate emotion intensity (0-1 scale)"""
        # Placeholder - would analyze facial muscle movements
        import random
        return round(random.uniform(0.4, 0.8), 2)  # Return Python float, not numpy

    def _calculate_emotion_confidence(self, frame):
        """Calculate confidence in emotion detection"""
        # Placeholder - would be based on model confidence scores
        import random
        return round(random.uniform(0.6, 0.9), 2)  # Return Python float, not numpy

    def _detect_micro_expressions_advanced(self, frame, primary_emotion):
        """Advanced micro-expression detection"""
        try:
            micro_expressions = []
            
            if not ADVANCED_LIBS_AVAILABLE or not self.landmark_predictor:
                # Basic micro-expression detection
                if primary_emotion == "positive":
                    micro_expressions = ["genuine_smile"]
                elif primary_emotion == "neutral":
                    micro_expressions = ["relaxed"]
                else:
                    micro_expressions = ["subtle_tension"]
            else:
                # Advanced micro-expression detection using facial landmarks
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_detector(gray)
                
                if len(faces) > 0:
                    landmarks = self.landmark_predictor(gray, faces[0])
                    
                    # Analyze specific facial regions for micro-expressions
                    micro_expressions = self._analyze_facial_micro_movements(landmarks, primary_emotion)
            
            return micro_expressions if micro_expressions else ["neutral"]
            
        except Exception as e:
            logger.error(f"❌ Micro-expression detection error: {e}")
            return ["neutral"]

    def _analyze_facial_micro_movements(self, landmarks, primary_emotion):
        """Analyze facial micro-movements for micro-expressions"""
        micro_expressions = []
        
        try:
            # Mouth corners analysis
            mouth_left = (landmarks.part(48).x, landmarks.part(48).y)
            mouth_right = (landmarks.part(54).x, landmarks.part(54).y)
            mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
            mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)
            
            # Calculate mouth curvature for smile analysis
            mouth_width = euclidean(mouth_left, mouth_right)
            mouth_height = euclidean(mouth_top, mouth_bottom)
            mouth_ratio = mouth_width / mouth_height if mouth_height > 0 else 0
            
            if mouth_ratio > 3.5:
                if primary_emotion == "positive":
                    micro_expressions.append("genuine_smile")
                else:
                    micro_expressions.append("forced_smile")
            
            # Eye region analysis for tension
            left_eyebrow = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(17, 22)]
            right_eyebrow = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(22, 27)]
            
            # Check for eyebrow tension (simplified)
            eyebrow_height_variance = np.var([p[1] for p in left_eyebrow + right_eyebrow])
            if eyebrow_height_variance > 20:
                micro_expressions.append("eyebrow_tension")
            
            # Nose flare detection (simplified)
            nose_left = (landmarks.part(31).x, landmarks.part(31).y)
            nose_right = (landmarks.part(35).x, landmarks.part(35).y)
            nose_width = euclidean(nose_left, nose_right)
            
            # This would need baseline comparison, simplified for demo
            if nose_width > 25:  # Placeholder threshold
                micro_expressions.append("slight_stress")
            
            return micro_expressions if micro_expressions else ["relaxed"]
            
        except Exception as e:
            logger.error(f"❌ Facial micro-movement analysis error: {e}")
            return ["neutral"]

    def _calculate_emotion_variability(self):
        """Calculate emotion variability from history"""
        if len(self.emotion_history) < 5:
            return "insufficient_data"
        
        unique_emotions = len(set(self.emotion_history))
        total_emotions = len(self.emotion_history)
        
        variability_ratio = unique_emotions / total_emotions
        
        if variability_ratio > 0.6:
            return "high"
        elif variability_ratio > 0.3:
            return "medium"
        else:
            return "low"

    def _analyze_posture_clean(self, frame):
        """Cleaned-up posture analysis"""
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
                    "face_size_rating": "no_face",
                    "face_centering": "no_face",
                    "posture_consistency": "unknown",
                    "distance_assessment": "unknown"
                }
            
            face = faces[0]
            frame_height, frame_width = frame.shape[:2]
            
            # Face size analysis
            if hasattr(face, 'width'):
                face_width = face.width()
                face_height = face.height()
            else:
                face_width = face[2]  # width for cv2.Rect
                face_height = face[3]  # height for cv2.Rect
            
            face_area_ratio = (face_width * face_height) / (frame_width * frame_height)
            
            # Face size rating
            if face_area_ratio < 0.04:
                face_size_rating = "too_small"
                distance_assessment = "too_far"
            elif face_area_ratio > 0.35:
                face_size_rating = "too_large"
                distance_assessment = "too_close"
            elif face_area_ratio < 0.08:
                face_size_rating = "small"
                distance_assessment = "slightly_far"
            elif face_area_ratio > 0.25:
                face_size_rating = "large"
                distance_assessment = "slightly_close"
            else:
                face_size_rating = "optimal"
                distance_assessment = "good_distance"
            
            # Face centering analysis
            if hasattr(face, 'center'):
                face_center_x = face.center().x
            else:
                face_center_x = face[0] + face_width // 2
            
            frame_center_x = frame_width // 2
            centering_offset = abs(face_center_x - frame_center_x) / frame_width
            
            if centering_offset < 0.08:
                face_centering = "centered"
            elif centering_offset < 0.15:
                face_centering = "slightly_off"
            else:
                face_centering = "off_center"
            
            # Posture consistency (would track over multiple frames)
            posture_consistency = "stable"  # Simplified for single frame
            
            return {
                "face_size_rating": face_size_rating,
                "face_centering": face_centering,
                "posture_consistency": posture_consistency,
                "distance_assessment": distance_assessment
            }
            
        except Exception as e:
            logger.error(f"❌ Posture analysis error: {e}")
            return {
                "face_size_rating": "unknown",
                "face_centering": "unknown",
                "posture_consistency": "unknown",
                "distance_assessment": "unknown"
            }

    def _analyze_body_language_clean(self, frame):
        """Enhanced body language analysis"""
        try:
            if not ADVANCED_LIBS_AVAILABLE or not self.landmark_predictor:
                return {
                    "head_tilt": "neutral",
                    "head_movement": "minimal",
                    "body_positioning": "centered"
                }
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_detector(gray)
            
            if len(faces) == 0:
                return {
                    "head_tilt": "unknown",
                    "head_movement": "unknown",
                    "body_positioning": "unknown"
                }
            
            landmarks = self.landmark_predictor(gray, faces[0])
            
            # Calculate head tilt using eye landmarks
            left_eye = (landmarks.part(36).x, landmarks.part(36).y)
            right_eye = (landmarks.part(45).x, landmarks.part(45).y)
            
            # Calculate tilt angle
            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            angle = math.degrees(math.atan2(dy, dx))
            
            # Classify head tilt
            if abs(angle) < 3:
                head_tilt = "neutral"
            elif 3 <= angle <= 15:
                head_tilt = "slight_right"
            elif angle > 15:
                head_tilt = "right"
            elif -15 <= angle <= -3:
                head_tilt = "slight_left"
            else:
                head_tilt = "left"
            
            # Track head movement over time
            self.head_tilt_history.append(angle)
            head_movement = self._calculate_head_movement()
            
            # Body positioning (simplified - would need upper body detection for full analysis)
            face_rect = faces[0]
            frame_center_x = frame.shape[1] // 2
            face_center_x = (face_rect.left() + face_rect.right()) // 2
            
            positioning_offset = abs(face_center_x - frame_center_x) / frame.shape[1]
            
            if positioning_offset < 0.1:
                body_positioning = "centered"
            elif positioning_offset < 0.2:
                body_positioning = "slightly_off"
            else:
                body_positioning = "off_center"
            
            return {
                "head_tilt": head_tilt,
                "head_movement": head_movement,
                "body_positioning": body_positioning
            }
            
        except Exception as e:
            logger.error(f"❌ Body language analysis error: {e}")
            return {
                "head_tilt": "neutral",
                "head_movement": "minimal",
                "body_positioning": "centered"
            }

    def _calculate_head_movement(self):
        """Calculate head movement based on tilt history"""
        if len(self.head_tilt_history) < 3:
            return "insufficient_data"
        
        recent_tilts = list(self.head_tilt_history)[-5:]
        # Use Python's statistics module instead of numpy
        mean_tilt = sum(recent_tilts) / len(recent_tilts)
        variance = sum((x - mean_tilt) ** 2 for x in recent_tilts) / len(recent_tilts)
        
        if variance < 2:
            return "minimal"
        elif variance < 8:
            return "moderate"
        else:
            return "excessive"

    def _calculate_engagement_metrics_clean(self, analysis):
        """Calculate engagement metrics - cleaned up"""
        try:
            engagement_score = 0.5  # Base score
            
            # Eye gaze contributes to engagement
            eye_gaze = analysis.get("eye_gaze_analysis", {})
            if eye_gaze.get("eye_gaze_direction") == "looking_at_camera":
                engagement_score += 0.25
                # Bonus for good eye contact confidence
                confidence = eye_gaze.get("eye_contact_confidence", 0)
                engagement_score += confidence * 0.15
            
            # Good posture contributes
            posture = analysis.get("posture_analysis", {})
            if posture.get("face_centering") in ["centered", "slightly_off"]:
                engagement_score += 0.1
            if posture.get("distance_assessment") in ["good_distance", "slightly_close", "slightly_far"]:
                engagement_score += 0.1
            
            # Emotion contributes
            emotion = analysis.get("emotion_analysis", {})
            if emotion.get("dominant_emotion") in ["positive", "focused", "engaged"]:
                engagement_score += 0.1
                # Bonus for emotion intensity
                intensity = emotion.get("emotion_intensity", 0)
                engagement_score += intensity * 0.05
            
            # Body language contributes
            body_lang = analysis.get("body_language", {})
            if body_lang.get("head_tilt") in ["neutral", "slight_left", "slight_right"]:
                engagement_score += 0.05
            if body_lang.get("body_positioning") in ["centered", "slightly_off"]:
                engagement_score += 0.05
            
            engagement_score = min(1.0, max(0.0, engagement_score))
            
            # Calculate focus consistency from gaze history
            if len(self.gaze_history) > 0:
                focus_consistency = len([x for x in self.gaze_history if x]) / len(self.gaze_history)
            else:
                focus_consistency = 0.5
            
            # Determine attention level
            if engagement_score > 0.8:
                attention_level = "high"
            elif engagement_score > 0.6:
                attention_level = "medium" 
            elif engagement_score > 0.4:
                attention_level = "low"
            else:
                attention_level = "very_low"
            
            # Calculate professionalism score
            professionalism_score = self._calculate_professionalism_score_clean(analysis)
            
            return {
                "engagement_score": round(engagement_score, 3),
                "professionalism_score": round(professionalism_score, 3),
                "attention_level": attention_level,
                "focus_consistency": round(focus_consistency, 3)
            }
            
        except Exception as e:
            logger.error(f"❌ Engagement metrics calculation error: {e}")
            return {
                "engagement_score": 0.5,
                "professionalism_score": 0.5,
                "attention_level": "unknown",
                "focus_consistency": 0.5
            }

    def _calculate_professionalism_score_clean(self, analysis):
        """Calculate professionalism score - cleaned up"""
        score = 0.4  # Base score
        
        # Good posture and positioning
        posture = analysis.get("posture_analysis", {})
        if posture.get("face_centering") == "centered":
            score += 0.15
        elif posture.get("face_centering") == "slightly_off":
            score += 0.1
        
        if posture.get("distance_assessment") == "good_distance":
            score += 0.15
        elif posture.get("distance_assessment") in ["slightly_close", "slightly_far"]:
            score += 0.1
        
        # Eye contact quality
        eye_gaze = analysis.get("eye_gaze_analysis", {})
        if eye_gaze.get("eye_gaze_direction") == "looking_at_camera":
            score += 0.15
            # Bonus for good gaze quality
            if eye_gaze.get("gaze_quality") in ["excellent", "good"]:
                score += 0.05
        
        # Body language
        body_lang = analysis.get("body_language", {})
        if body_lang.get("head_tilt") == "neutral":
            score += 0.05
        elif body_lang.get("head_tilt") in ["slight_left", "slight_right"]:
            score += 0.03
        
        if body_lang.get("head_movement") == "minimal":
            score += 0.05
        
        # Emotional appropriateness
        emotion = analysis.get("emotion_analysis", {})
        if emotion.get("dominant_emotion") in ["positive", "neutral", "focused"]:
            score += 0.05
        
        return min(1.0, max(0.0, score))

    def _calculate_confidence_indicators_clean(self, analysis):
        """Calculate confidence indicators - cleaned up"""
        try:
            # Base confidence calculation
            base_confidence = 0.5
            
            # Eye contact confidence
            eye_gaze = analysis.get("eye_gaze_analysis", {})
            eye_confidence = eye_gaze.get("eye_contact_confidence", 0.5)
            
            # Posture confidence factors
            posture = analysis.get("posture_analysis", {})
            posture_factors = 0
            if posture.get("posture_consistency") == "stable":
                posture_factors += 0.3
            if posture.get("face_centering") == "centered":
                posture_factors += 0.2
            if posture.get("distance_assessment") == "good_distance":
                posture_factors += 0.2
            
            # Body language confidence
            body_lang = analysis.get("body_language", {})
            body_confidence = 0
            if body_lang.get("head_tilt") == "neutral":
                body_confidence += 0.2
            if body_lang.get("head_movement") == "minimal":
                body_confidence += 0.1
            
            # Overall confidence score
            confidence_score = (base_confidence + eye_confidence + posture_factors + body_confidence) / 4
            confidence_score = min(1.0, max(0.0, confidence_score))
            
            # Eye contact duration estimation (simplified)
            if eye_gaze.get("eye_gaze_direction") == "looking_at_camera":
                eye_contact_duration = min(5.0, 2.0 + eye_confidence * 2)
            else:
                eye_contact_duration = max(0.1, eye_confidence * 1.5)
            
            # Posture confidence classification
            if posture_factors > 0.6:
                posture_confidence = "high"
            elif posture_factors > 0.3:
                posture_confidence = "medium"
            else:
                posture_confidence = "low"
            
            # Store confidence metrics for trending
            self.confidence_metrics.append(confidence_score)
            
            return {
                "confidence_score": round(confidence_score, 3),
                "eye_contact_duration": round(eye_contact_duration, 1),
                "posture_confidence": posture_confidence
            }
            
        except Exception as e:
            logger.error(f"❌ Confidence indicators calculation error: {e}")
            return {
                "confidence_score": 0.5,
                "eye_contact_duration": 1.0,
                "posture_confidence": "medium"
            }

    def _analyze_distractions_clean(self, analysis):
        """Analyze distractions and attention breaks - cleaned up"""
        try:
            distraction_flags = []
            attention_breaks = 0
            
            # Check for gaze-based distractions
            eye_gaze = analysis.get("eye_gaze_analysis", {})
            gaze_direction = eye_gaze.get("eye_gaze_direction", "")
            
            if gaze_direction in ["gaze_averted", "looking_left", "looking_right", "looking_up", "looking_down"]:
                distraction_flags.append("gaze_distraction")
                attention_breaks += 1
            
            if eye_gaze.get("eyes_closed", False):
                distraction_flags.append("eyes_closed")
                attention_breaks += 1
            
            # Check for positioning distractions
            posture = analysis.get("posture_analysis", {})
            if posture.get("face_centering") == "off_center":
                distraction_flags.append("poor_positioning")
            
            if posture.get("distance_assessment") in ["too_close", "too_far"]:
                distraction_flags.append("distance_issue")
            
            # Check for body language distractions
            body_lang = analysis.get("body_language", {})
            if body_lang.get("head_movement") == "excessive":
                distraction_flags.append("excessive_movement")
                attention_breaks += 1
            
            if body_lang.get("head_tilt") in ["left", "right"]:
                distraction_flags.append("head_tilt_distraction")
            
            # Calculate gaze stability from recent history
            if len(self.gaze_history) >= 5:
                recent_gaze = list(self.gaze_history)[-10:]
                stability_ratio = len([x for x in recent_gaze if x]) / len(recent_gaze)
                
                if stability_ratio > 0.8:
                    gaze_stability = "stable"
                elif stability_ratio > 0.6:
                    gaze_stability = "mostly_stable"
                elif stability_ratio > 0.4:
                    gaze_stability = "somewhat_unstable"
                else:
                    gaze_stability = "unstable"
            else:
                gaze_stability = "insufficient_data"
            
            return {
                "distraction_flags": distraction_flags,
                "attention_breaks": attention_breaks,
                "gaze_stability": gaze_stability
            }
            
        except Exception as e:
            logger.error(f"❌ Distraction analysis error: {e}")
            return {
                "distraction_flags": [],
                "attention_breaks": 0,
                "gaze_stability": "unknown"
            }

    def _basic_gaze_analysis_clean(self, frame):
        """Basic gaze analysis fallback - cleaned up"""
        # Simplified gaze detection using basic computer vision
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use eye cascade for basic detection
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(eyes) >= 2:
                gaze_direction = "looking_at_camera"
                eyes_closed = False
                confidence = 0.6
                gaze_quality = "fair"
            elif len(eyes) == 1:
                gaze_direction = "partially_obscured"
                eyes_closed = False
                confidence = 0.3
                gaze_quality = "poor"
            else:
                gaze_direction = "gaze_averted"
                eyes_closed = True
                confidence = 0.2
                gaze_quality = "poor"
            
            return {
                "eye_gaze_direction": gaze_direction,
                "eyes_closed": eyes_closed,
                "eye_contact_confidence": confidence,
                "gaze_quality": gaze_quality
            }
            
        except Exception as e:
            logger.error(f"❌ Basic gaze analysis error: {e}")
            return {
                "eye_gaze_direction": "unknown",
                "eyes_closed": False,
                "eye_contact_confidence": 0.5,
                "gaze_quality": "unknown"
            }

    def _classify_gaze_quality(self, confidence):
        """Classify gaze quality based on confidence"""
        if confidence > 0.85:
            return "excellent"
        elif confidence > 0.7:
            return "good"
        elif confidence > 0.5:
            return "fair"
        elif confidence > 0.3:
            return "poor"
        else:
            return "very_poor"

    def _create_error_frame_data(self, frame_number, timestamp):
        """Create error frame data structure - cleaned up"""
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
                "eye_gaze_direction": "error",
                "eyes_closed": False,
                "eye_contact_confidence": 0.0,
                "gaze_quality": "error"
            },
            "emotion_analysis": {
                "dominant_emotion": "unknown",
                "emotion_intensity": 0.0,
                "emotion_confidence": 0.0,
                "micro_expressions": ["unknown"],
                "emotion_variability": "unknown"
            },
            "posture_analysis": {
                "face_size_rating": "unknown",
                "face_centering": "unknown",
                "posture_consistency": "unknown",
                "distance_assessment": "unknown"
            },
            "body_language": {
                "head_tilt": "unknown",
                "head_movement": "unknown",
                "body_positioning": "unknown"
            },
            "engagement_metrics": {
                "engagement_score": 0.0,
                "professionalism_score": 0.0,
                "attention_level": "unknown",
                "focus_consistency": 0.0
            },
            "confidence_indicators": {
                "confidence_score": 0.0,
                "eye_contact_duration": 0.0,
                "posture_confidence": "unknown"
            },
            "distraction_analysis": {
                "distraction_flags": ["analysis_error"],
                "attention_breaks": 0,
                "gaze_stability": "unknown"
            }
        }


class EnhancedFrameProcessor:
    def __init__(self, session_id, interview_id):
        self.session_id = session_id
        self.interview_id = interview_id
        self.user_id = self._extract_user_id_from_session(session_id)
        
        self.frames_processed_count = 0
        self.frames_found_count = 0
        self.messages_scanned = 0
        self.session_messages_found = 0
        
        # Initialize advanced analyzer
        self.analyzer = AdvancedFrameAnalyzer()
        
        logger.info(f"🚀 Initialized EnhancedFrameProcessor with Cleaned Analysis Structure")
        logger.info(f"   Session: {self.session_id}")
        logger.info(f"   Interview: {self.interview_id}")
        logger.info(f"   User: {self.user_id}")
        logger.info(f"   Advanced libs available: {ADVANCED_LIBS_AVAILABLE}")

    def _extract_user_id_from_session(self, session_id):
        """Extract user_id from session_id format"""
        try:
            parts = session_id.split('_')
            return parts[0] if len(parts) >= 4 else 'unknown'
        except:
            return 'unknown'

    def process_frames(self):
        """Main processing function"""
        logger.info(f"🎥 Starting ENHANCED frame processing with cleaned structure for session: {self.session_id}")
        self._scan_kafka_messages()

        if self.frames_found_count > 0:
            self._process_session_frames()
        else:
            logger.warning(f"⚠️ No frame messages found for session {self.session_id}")

        return self._finalize_enhanced_analysis()

    def _scan_kafka_messages(self):
        """Scan Kafka messages for session frames"""
        try:
            logger.info(f"📡 Starting enhanced Kafka scan for session: {self.session_id}")

            kafka_config = KAFKA_CONFIG.copy()
            kafka_config['group_id'] = None

            consumer = KafkaConsumer(**kafka_config)
            partition = TopicPartition(KAFKA_TOPIC, 0)
            consumer.assign([partition])
            consumer.seek_to_beginning(partition)

            scan_start_time = time.time()
            max_scan_time = 1300

            for message_batch in consumer:
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
                            logger.info(f"🎬 Found frame {self.frames_found_count} for session {self.session_id}")
                            self._store_frame_message(message_data)

                    if self.messages_scanned % 100 == 0:
                        logger.info(f"📊 Scanned {self.messages_scanned} messages, "
                                  f"session messages: {self.session_messages_found}, "
                                  f"frames found: {self.frames_found_count}")

                except Exception as e:
                    logger.error(f"❌ Error processing message {self.messages_scanned}: {e}")
                    continue

            consumer.close()

            scan_duration = time.time() - scan_start_time
            logger.info(f"✅ Kafka scan completed in {scan_duration:.2f}s")
            logger.info(f"📊 Total messages scanned: {self.messages_scanned}")
            logger.info(f"🎯 Session messages found: {self.session_messages_found}")
            logger.info(f"🎬 Frame messages found: {self.frames_found_count}")

        except Exception as e:
            logger.error(f"❌ Enhanced Kafka scanning failed: {e}")

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
            if not os.path.exists(frames_dir):
                logger.warning(f"⚠️ Frames directory not found: {frames_dir}")
                return

            frame_files = sorted([f for f in os.listdir(frames_dir) if f.startswith('frame_')])
            logger.info(f"🎬 Processing {len(frame_files)} stored frame messages with cleaned analysis")

            for i, frame_file in enumerate(frame_files):
                try:
                    frame_path = os.path.join(frames_dir, frame_file)
                    with open(frame_path, 'r') as f:
                        message_data = json.load(f)

                    success = self._process_single_frame_message(message_data, i + 1)
                    if success:
                        self.frames_processed_count += 1

                    if self.frames_processed_count % 5 == 0:
                        logger.info(f"📈 Progress: {self.frames_processed_count}/{len(frame_files)} frames processed")

                except Exception as e:
                    logger.error(f"❌ Error processing frame file {frame_file}: {e}")

            # Cleanup
            try:
                import shutil
                shutil.rmtree(frames_dir)
                logger.info(f"🧹 Cleaned up temporary frames directory")
            except Exception as e:
                logger.warning(f"⚠️ Could not cleanup frames directory: {e}")

        except Exception as e:
            logger.error(f"❌ Error in frame processing: {e}")

    def _process_single_frame_message(self, message_dict, frame_number):
        """Process a single frame message with cleaned enhanced analysis"""
        try:
            # Extract frame data
            frame_b64 = self._extract_frame_data(message_dict)
            if not frame_b64:
                return False

            # Decode frame
            try:
                frame_bytes = base64.b64decode(frame_b64)
                frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                if frame is None:
                    return False

                height, width = frame.shape[:2]
                if height < 100 or width < 100:
                    return False

            except Exception as e:
                logger.error(f"❌ Frame decoding error: {e}")
                return False

            # Perform comprehensive cleaned analysis
            timestamp = message_dict.get('timestamp', time.time())
            analysis_result = self.analyzer.analyze_frame_comprehensive(frame, frame_number, timestamp)

            # Convert numpy types to Python native types for JSON serialization
            analysis_result = self._convert_numpy_types(analysis_result)

            # Store analysis result
            analysis_file = f"/tmp/analysis_{self.session_id}_{frame_number}.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_result, f, indent=2)

            logger.info(f"✅ Cleaned enhanced analysis completed for frame {frame_number}")
            return True

        except Exception as e:
            logger.error(f"❌ Error in single frame processing: {e}")
            return False

    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

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

    def _finalize_enhanced_analysis(self):
        """Finalize and save comprehensive cleaned analysis"""
        try:
            logger.info(f"📊 Generating comprehensive cleaned analysis report for session: {self.session_id}")

            # Collect all frame analyses
            frame_analyses = []
            for i in range(1, self.frames_processed_count + 1):
                analysis_file = f"/tmp/analysis_{self.session_id}_{i}.json"
                if os.path.exists(analysis_file):
                    with open(analysis_file, 'r') as f:
                        frame_analysis = json.load(f)
                        frame_analyses.append(frame_analysis)
                    os.remove(analysis_file)  # Cleanup

            # Generate session summary
            session_summary = self._generate_session_summary_clean(frame_analyses)

            # Create comprehensive report
            timestamp = int(time.time())
            hash_part = self.session_id.split('_')[-1] if '_' in self.session_id else 'nohash'
            output_filename = f"cleaned_analysis_{self.user_id}_{self.interview_id}_{timestamp}_{hash_part}.json"
            output_path = f"/app/{output_filename}"

            comprehensive_report = {
                'metadata': {
                    'session_id': self.session_id,
                    'user_id': self.user_id,
                    'interview_id': self.interview_id,
                    'timestamp': timestamp,
                    'frames_processed': self.frames_processed_count,
                    'frames_found': self.frames_found_count,
                    'analysis_type': 'comprehensive_cleaned_enhanced',
                    'filename': output_filename,
                    'advanced_libs_available': ADVANCED_LIBS_AVAILABLE,
                    'duplicate_keys_removed': True
                },
                'processing_stats': {
                    'messages_scanned': self.messages_scanned,
                    'session_messages_found': self.session_messages_found,
                    'frames_found': self.frames_found_count,
                    'frames_processed': self.frames_processed_count,
                    'processing_success_rate': (self.frames_processed_count / max(1, self.frames_found_count)) * 100,
                    'processing_method': 'enhanced_cleaned_comprehensive_processor'
                },
                'session_summary': session_summary,
                'overall_interview_analysis': self._generate_overall_interview_analysis(session_summary),
                'frame_analyses': frame_analyses  # Include ALL frame analyses, not just first 10
            }

            with open(output_path, 'w') as f:
                json.dump(comprehensive_report, f, indent=4, default=str)

            logger.info(f"✅ Comprehensive cleaned analysis report saved to: {output_path}")
            logger.info(f"📁 Enhanced filename: {output_filename}")
            logger.info(f"📊 Frame analyses included: {len(frame_analyses)} out of {self.frames_processed_count} processed")
            logger.info(f"📈 Final Processing Summary:")
            logger.info(f"   • Messages scanned: {self.messages_scanned}")
            logger.info(f"   • Session messages: {self.session_messages_found}")
            logger.info(f"   • Frames found: {self.frames_found_count}")
            logger.info(f"   • Frames processed: {self.frames_processed_count}")
            logger.info(f"   • Duplicate keys removed: ✅")
            logger.info(f"   • Advanced analysis: {ADVANCED_LIBS_AVAILABLE}")
            logger.info(f"   • All frames included in output: ✅")

            return True

        except Exception as e:
            logger.error(f"❌ Enhanced cleaned analysis finalization failed: {e}")
            return False

    def _generate_session_summary_clean(self, frame_analyses):
        """Generate comprehensive session summary - cleaned up"""
        if not frame_analyses:
            return {"error": "No frame analyses available"}

        try:
            total_frames = len(frame_analyses)
            
            # Eye contact statistics
            looking_at_camera_frames = sum(1 for f in frame_analyses 
                                         if f.get('eye_gaze_analysis', {}).get('eye_gaze_direction') == 'looking_at_camera')
            eye_contact_percentage = (looking_at_camera_frames / total_frames) * 100
            
            # Engagement statistics
            engagement_scores = [f.get('engagement_metrics', {}).get('engagement_score', 0) 
                               for f in frame_analyses]
            avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
            
            # Confidence statistics
            confidence_scores = [f.get('confidence_indicators', {}).get('confidence_score', 0) 
                               for f in frame_analyses]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Emotion analysis
            emotions = [f.get('emotion_analysis', {}).get('dominant_emotion', 'unknown') 
                       for f in frame_analyses]
            emotion_distribution = {emotion: emotions.count(emotion) for emotion in set(emotions)}
            
            # Professional presence
            prof_scores = [f.get('engagement_metrics', {}).get('professionalism_score', 0) 
                          for f in frame_analyses]
            avg_professionalism = sum(prof_scores) / len(prof_scores) if prof_scores else 0

            # Distraction analysis
            total_distractions = sum(len(f.get('distraction_analysis', {}).get('distraction_flags', [])) 
                                   for f in frame_analyses)
            total_attention_breaks = sum(f.get('distraction_analysis', {}).get('attention_breaks', 0) 
                                       for f in frame_analyses)

            # Gaze quality analysis
            gaze_qualities = [f.get('eye_gaze_analysis', {}).get('gaze_quality', 'unknown') 
                            for f in frame_analyses]
            gaze_quality_distribution = {quality: gaze_qualities.count(quality) for quality in set(gaze_qualities)}

            return {
                'total_frames_analyzed': total_frames,
                'eye_contact_statistics': {
                    'percentage_looking_at_camera': round(eye_contact_percentage, 2),
                    'total_eye_contact_frames': looking_at_camera_frames,
                    'gaze_quality_distribution': gaze_quality_distribution
                },
                'engagement_analysis': {
                    'average_engagement_score': round(avg_engagement, 3),
                    'engagement_level': self._classify_level(avg_engagement),
                    'engagement_consistency': round(self._calculate_std_dev(engagement_scores), 3) if engagement_scores else 0
                },
                'confidence_analysis': {
                    'average_confidence_score': round(avg_confidence, 3),
                    'confidence_level': self._classify_level(avg_confidence),
                    'confidence_trend': self._analyze_trend(confidence_scores)
                },
                'emotion_analysis': {
                    'emotion_distribution': emotion_distribution,
                    'dominant_session_emotion': max(emotion_distribution, key=emotion_distribution.get) if emotion_distribution else 'unknown',
                    'emotion_consistency': self._calculate_emotion_consistency(emotions)
                },
                'professionalism_analysis': {
                    'average_professionalism_score': round(avg_professionalism, 3),
                    'professionalism_level': self._classify_professionalism_level(avg_professionalism)
                },
                'distraction_analysis': {
                    'total_distraction_flags': total_distractions,
                    'total_attention_breaks': total_attention_breaks,
                    'distraction_rate': round((total_distractions / total_frames) * 100, 2),
                    'attention_break_rate': round((total_attention_breaks / total_frames) * 100, 2)
                },
                'overall_assessment': {
                    'session_quality': self._assess_session_quality(avg_engagement, avg_confidence, total_distractions),
                    'key_strengths': self._identify_strengths_clean(frame_analyses),
                    'improvement_areas': self._identify_improvement_areas_clean(frame_analyses),
                    'overall_score': round((avg_engagement + avg_confidence + avg_professionalism) / 3, 3)
                }
            }

        except Exception as e:
            logger.error(f"❌ Session summary generation error: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}

    def _calculate_std_dev(self, values):
        """Calculate standard deviation using Python native functions"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _classify_level(self, score):
        """Classify score into level categories"""
        if score > 0.8:
            return "excellent"
        elif score > 0.7:
            return "high"
        elif score > 0.6:
            return "good"
        elif score > 0.4:
            return "medium"
        elif score > 0.2:
            return "low"
        else:
            return "very_low"

    def _classify_professionalism_level(self, score):
        """Classify professionalism score"""
        if score > 0.9:
            return "exceptional"
        elif score > 0.8:
            return "excellent"
        elif score > 0.7:
            return "very_good"
        elif score > 0.6:
            return "good"
        elif score > 0.4:
            return "needs_improvement"
        else:
            return "poor"

    def _analyze_trend(self, scores):
        """Analyze trend in scores"""
        if len(scores) < 3:
            return "insufficient_data"
        
        # Simple trend analysis using Python native functions
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        diff = second_avg - first_avg
        
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def _calculate_emotion_consistency(self, emotions):
        """Calculate emotion consistency"""
        if len(emotions) < 3:
            return "insufficient_data"
        
        most_common = max(set(emotions), key=emotions.count)
        consistency_rate = emotions.count(most_common) / len(emotions)
        
        if consistency_rate > 0.8:
            return "very_consistent"
        elif consistency_rate > 0.6:
            return "consistent"
        elif consistency_rate > 0.4:
            return "somewhat_consistent"
        else:
            return "inconsistent"

    def _assess_session_quality(self, engagement, confidence, total_distractions_count):
        """Assess overall session quality"""
        base_score = (engagement + confidence) / 2
        
        # Calculate distraction penalty based on distraction rate, not count
        total_frames = len(self.confidence_metrics) if hasattr(self, 'confidence_metrics') else 100
        distraction_rate = total_distractions_count / max(1, total_frames)
        distraction_penalty = min(0.3, distraction_rate * 0.5)  # Reduced penalty
        
        final_score = max(0, base_score - distraction_penalty)
        
        if final_score > 0.8:
            return "exceptional"
        elif final_score > 0.7:
            return "excellent" 
        elif final_score > 0.6:
            return "very_good"
        elif final_score > 0.5:
            return "good"
        elif final_score > 0.35:
            return "needs_improvement"
        else:
            return "poor"

    def _generate_overall_interview_analysis(self, session_summary):
        """Generate comprehensive overall interview analysis"""
        try:
            # Extract key metrics
            eye_contact_percentage = session_summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
            avg_engagement = session_summary.get('engagement_analysis', {}).get('average_engagement_score', 0)
            avg_confidence = session_summary.get('confidence_analysis', {}).get('average_confidence_score', 0)
            avg_professionalism = session_summary.get('professionalism_analysis', {}).get('average_professionalism_score', 0)
            distraction_rate = session_summary.get('distraction_analysis', {}).get('distraction_rate', 0)
            
            # Overall performance rating
            overall_score = session_summary.get('overall_assessment', {}).get('overall_score', 0)
            session_quality = session_summary.get('overall_assessment', {}).get('session_quality', 'unknown')
            
            # Detailed analysis
            analysis = {
                'overall_performance': {
                    'session_quality': session_quality,
                    'overall_score': overall_score,
                    'performance_level': self._get_performance_level(overall_score),
                    'interview_readiness': self._assess_interview_readiness(eye_contact_percentage, avg_engagement, avg_professionalism)
                },
                'key_metrics_summary': {
                    'eye_contact_percentage': f"{eye_contact_percentage}%",
                    'engagement_level': session_summary.get('engagement_analysis', {}).get('engagement_level', 'unknown'),
                    'confidence_level': session_summary.get('confidence_analysis', {}).get('confidence_level', 'unknown'),
                    'professionalism_level': session_summary.get('professionalism_analysis', {}).get('professionalism_level', 'unknown'),
                    'distraction_rate': f"{distraction_rate}%"
                },
                'strengths_analysis': {
                    'primary_strengths': session_summary.get('overall_assessment', {}).get('key_strengths', []),
                    'detailed_strengths': self._detailed_strengths_analysis(session_summary),
                    'what_went_well': self._what_went_well(session_summary)
                },
                'improvement_recommendations': {
                    'primary_areas': session_summary.get('overall_assessment', {}).get('improvement_areas', []),
                    'detailed_recommendations': self._detailed_improvement_recommendations(session_summary),
                    'action_items': self._generate_action_items(session_summary)
                },
                'interview_feedback': {
                    'positive_highlights': self._generate_positive_highlights(session_summary),
                    'areas_to_work_on': self._generate_areas_to_work_on(session_summary),
                    'overall_impression': self._generate_overall_impression(session_summary),
                    'interviewer_perspective': self._generate_interviewer_perspective(session_summary)
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Overall interview analysis generation error: {e}")
            return {"error": f"Overall analysis generation failed: {str(e)}"}

    def _get_performance_level(self, score):
        """Get performance level description"""
        if score > 0.9:
            return "exceptional_performance"
        elif score > 0.8:
            return "excellent_performance"  
        elif score > 0.7:
            return "very_good_performance"
        elif score > 0.6:
            return "good_performance"
        elif score > 0.5:
            return "average_performance"
        else:
            return "needs_significant_improvement"

    def _assess_interview_readiness(self, eye_contact, engagement, professionalism):
        """Assess overall interview readiness"""
        readiness_score = (eye_contact/100 + engagement + professionalism) / 3
        
        if readiness_score > 0.8:
            return "fully_ready"
        elif readiness_score > 0.7:
            return "mostly_ready"
        elif readiness_score > 0.6:
            return "needs_minor_improvements"
        elif readiness_score > 0.5:
            return "needs_moderate_improvements"
        else:
            return "needs_significant_preparation"

    def _detailed_strengths_analysis(self, summary):
        """Generate detailed strengths analysis"""
        strengths = []
        
        eye_contact_pct = summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
        if eye_contact_pct > 70:
            strengths.append("Maintains excellent eye contact throughout the interview")
        elif eye_contact_pct > 50:
            strengths.append("Shows good eye contact habits")
            
        engagement_level = summary.get('engagement_analysis', {}).get('engagement_level', '')
        if engagement_level in ['high', 'excellent']:
            strengths.append("Demonstrates high level of engagement and attentiveness")
            
        prof_level = summary.get('professionalism_analysis', {}).get('professionalism_level', '')
        if prof_level in ['excellent', 'very_good']:
            strengths.append("Exhibits strong professional presence and demeanor")
            
        return strengths

    def _what_went_well(self, summary):
        """Generate what went well analysis"""
        positives = []
        
        gaze_quality = summary.get('eye_contact_statistics', {}).get('gaze_quality_distribution', {})
        excellent_gaze = gaze_quality.get('excellent', 0)
        if excellent_gaze > 50:
            positives.append("Consistent high-quality eye contact")
            
        emotion_dist = summary.get('emotion_analysis', {}).get('emotion_distribution', {})
        positive_emotions = emotion_dist.get('positive', 0)
        total_frames = summary.get('total_frames_analyzed', 1)
        if positive_emotions / total_frames > 0.7:
            positives.append("Maintained positive emotional state")
            
        distraction_rate = summary.get('distraction_analysis', {}).get('distraction_rate', 100)
        if distraction_rate < 20:
            positives.append("Minimal distractions and strong focus")
            
        return positives

    def _detailed_improvement_recommendations(self, summary):
        """Generate detailed improvement recommendations"""
        recommendations = []
        
        eye_contact_pct = summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
        if eye_contact_pct < 60:
            recommendations.append("Practice maintaining more consistent eye contact with the camera")
            
        confidence_level = summary.get('confidence_analysis', {}).get('confidence_level', '')
        if confidence_level in ['low', 'very_low']:
            recommendations.append("Work on building confidence through practice and preparation")
            
        distraction_rate = summary.get('distraction_analysis', {}).get('distraction_rate', 0)
        if distraction_rate > 40:
            recommendations.append("Minimize distractions and improve focus during interviews")
            
        engagement_level = summary.get('engagement_analysis', {}).get('engagement_level', '')
        if engagement_level in ['low', 'medium']:
            recommendations.append("Increase engagement through active listening and responsive body language")
            
        return recommendations

    def _generate_action_items(self, summary):
        """Generate specific action items"""
        actions = []
        
        # Eye contact improvements
        eye_contact_pct = summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
        if eye_contact_pct < 70:
            actions.append("Practice looking directly at camera for 3-5 seconds at a time")
            
        # Posture and positioning
        prof_score = summary.get('professionalism_analysis', {}).get('average_professionalism_score', 0)
        if prof_score < 0.8:
            actions.append("Ensure proper camera positioning and maintain good posture")
            
        # Distraction management
        distraction_rate = summary.get('distraction_analysis', {}).get('distraction_rate', 0)
        if distraction_rate > 30:
            actions.append("Create a distraction-free environment for interviews")
            
        return actions

    def _generate_positive_highlights(self, summary):
        """Generate positive highlights for feedback"""
        highlights = []
        
        overall_score = summary.get('overall_assessment', {}).get('overall_score', 0)
        if overall_score > 0.7:
            highlights.append("Strong overall interview performance")
            
        eye_contact_pct = summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
        if eye_contact_pct > 65:
            highlights.append("Excellent eye contact and engagement")
            
        emotion_consistency = summary.get('emotion_analysis', {}).get('emotion_consistency', '')
        if emotion_consistency == 'consistent':
            highlights.append("Maintained consistent positive demeanor")
            
        return highlights

    def _generate_areas_to_work_on(self, summary):
        """Generate areas to work on"""
        areas = []
        
        confidence_level = summary.get('confidence_analysis', {}).get('confidence_level', '')
        if confidence_level in ['low', 'medium']:
            areas.append("Building confidence and self-assurance")
            
        distraction_rate = summary.get('distraction_analysis', {}).get('distraction_rate', 0)
        if distraction_rate > 25:
            areas.append("Reducing distractions and improving focus")
            
        engagement_level = summary.get('engagement_analysis', {}).get('engagement_level', '')
        if engagement_level in ['medium', 'low']:
            areas.append("Increasing engagement and active participation")
            
        return areas

    def _generate_overall_impression(self, summary):
        """Generate overall impression"""
        session_quality = summary.get('overall_assessment', {}).get('session_quality', '')
        overall_score = summary.get('overall_assessment', {}).get('overall_score', 0)
        
        if session_quality in ['exceptional', 'excellent']:
            return "Candidate demonstrated excellent interview skills and professional presence"
        elif session_quality in ['very_good', 'good']:
            return "Candidate showed good interview performance with some areas for improvement"
        elif session_quality == 'needs_improvement':
            return "Candidate has potential but needs focused practice on key interview skills"
        else:
            return "Candidate would benefit from significant interview preparation and practice"

    def _generate_interviewer_perspective(self, summary):
        """Generate interviewer perspective"""
        eye_contact_pct = summary.get('eye_contact_statistics', {}).get('percentage_looking_at_camera', 0)
        prof_score = summary.get('professionalism_analysis', {}).get('average_professionalism_score', 0)
        engagement_score = summary.get('engagement_analysis', {}).get('average_engagement_score', 0)
        
        if eye_contact_pct > 70 and prof_score > 0.8 and engagement_score > 0.8:
            return "Would make a positive impression on interviewers with strong presence and engagement"
        elif eye_contact_pct > 50 and prof_score > 0.6:
            return "Would make a reasonable impression but could strengthen key areas"
        else:
            return "Would benefit from additional preparation to make a strong first impression"

    def _identify_strengths_clean(self, frame_analyses):
        """Identify key strengths from cleaned analysis"""
        strengths = []
        total_frames = len(frame_analyses)
        
        # Eye contact strength
        eye_contact_rate = sum(1 for f in frame_analyses 
                              if f.get('eye_gaze_analysis', {}).get('eye_gaze_direction') == 'looking_at_camera') / total_frames
        if eye_contact_rate > 0.8:
            strengths.append("excellent_eye_contact")
        elif eye_contact_rate > 0.6:
            strengths.append("good_eye_contact")
        
        # Engagement strength
        avg_engagement = sum(f.get('engagement_metrics', {}).get('engagement_score', 0) 
                           for f in frame_analyses) / total_frames
        if avg_engagement > 0.8:
            strengths.append("high_engagement")
        
        # Posture consistency
        stable_posture = sum(1 for f in frame_analyses 
                           if f.get('posture_analysis', {}).get('posture_consistency') == 'stable') / total_frames
        if stable_posture > 0.8:
            strengths.append("consistent_posture")
        
        # Professional presence
        avg_professionalism = sum(f.get('engagement_metrics', {}).get('professionalism_score', 0) 
                                for f in frame_analyses) / total_frames
        if avg_professionalism > 0.85:
            strengths.append("excellent_professionalism")
        
        # Low distraction rate
        total_distractions = sum(len(f.get('distraction_analysis', {}).get('distraction_flags', [])) 
                               for f in frame_analyses)
        if total_distractions / total_frames < 0.2:
            strengths.append("minimal_distractions")
        
        return strengths

    def _identify_improvement_areas_clean(self, frame_analyses):
        """Identify areas for improvement from cleaned analysis"""
        improvements = []
        total_frames = len(frame_analyses)
        
        # Eye contact issues
        poor_gaze_rate = sum(1 for f in frame_analyses 
                           if f.get('eye_gaze_analysis', {}).get('eye_gaze_direction') in ['gaze_averted', 'looking_left', 'looking_right']) / total_frames
        if poor_gaze_rate > 0.3:
            improvements.append("improve_eye_contact")
        
        # Positioning issues
        poor_centering = sum(1 for f in frame_analyses 
                           if f.get('posture_analysis', {}).get('face_centering') == 'off_center') / total_frames
        if poor_centering > 0.4:
            improvements.append("improve_camera_positioning")
        
        # Distance issues
        distance_issues = sum(1 for f in frame_analyses 
                            if f.get('posture_analysis', {}).get('distance_assessment') in ['too_close', 'too_far']) / total_frames
        if distance_issues > 0.3:
            improvements.append("adjust_camera_distance")
        
        # Excessive movement
        movement_issues = sum(1 for f in frame_analyses 
                            if f.get('body_language', {}).get('head_movement') == 'excessive') / total_frames
        if movement_issues > 0.2:
            improvements.append("reduce_excessive_movement")
        
        # Low engagement
        avg_engagement = sum(f.get('engagement_metrics', {}).get('engagement_score', 0) 
                           for f in frame_analyses) / total_frames
        if avg_engagement < 0.6:
            improvements.append("increase_engagement")
        
        # High distraction rate
        total_distractions = sum(len(f.get('distraction_analysis', {}).get('distraction_flags', [])) 
                               for f in frame_analyses)
        if total_distractions / total_frames > 0.5:
            improvements.append("reduce_distractions")
        
        return improvements


def main():
    parser = argparse.ArgumentParser(description="Enhanced Video Frame Analyzer with Cleaned Comprehensive Analysis")
    parser.add_argument('--session_id', required=True, help='Session ID for the interview')
    parser.add_argument('--interview_id', required=True, type=int, help='Interview ID')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🚀 Starting Enhanced Comprehensive Video Frame Analysis with Cleaned Structure")
    logger.info(f"   Session ID: {args.session_id}")
    logger.info(f"   Interview ID: {args.interview_id}")
    logger.info(f"   Advanced Libraries: {ADVANCED_LIBS_AVAILABLE}")
    logger.info(f"   Duplicate Keys Removed: ✅")

    if args.auto_process:
        try:
            processor = EnhancedFrameProcessor(
                session_id=args.session_id,
                interview_id=args.interview_id
            )

            success = processor.process_frames()

            if success:
                logger.info(f"🎉 Enhanced comprehensive video analysis with cleaned structure completed successfully!")
                logger.info(f"📊 Final Stats: {processor.frames_processed_count} frames processed from {processor.frames_found_count} found")
                logger.info(f"✨ Key improvements: Removed duplicate keys, enhanced micro-expressions, better gaze tracking")
                sys.exit(0)
            else:
                logger.error(f"💥 Enhanced comprehensive video analysis failed!")
                sys.exit(1)

        except Exception as e:
            logger.error(f"❌ Fatal error in enhanced comprehensive processing: {e}")
            sys.exit(1)
    else:
        logger.info(f"ℹ️ Use --auto_process to start analysis")
        logger.info(f"📋 Cleaned Analysis Structure:")
        logger.info(f"   • Removed duplicate keys (eye_gaze_direction vs looking_at_camera)")
        logger.info(f"   • Enhanced micro-expression detection")
        logger.info(f"   • Improved gaze direction classification")
        logger.info(f"   • Better emotion variability tracking")
        logger.info(f"   • Streamlined confidence indicators")

if __name__ == "__main__":
    main()
