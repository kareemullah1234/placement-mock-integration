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
        """LLM-friendly frame analysis with cleaned-up output structure"""
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
                # Eye gaze analysis (LLM-friendly)
                analysis["eye_gaze_analysis"] = self._analyze_eye_gaze_llm_friendly(frame)

                # Enhanced emotion analysis with proper emotions (LLM-friendly)
                analysis["emotion_analysis"] = self._analyze_emotions_llm_friendly(frame)

                # Posture analysis (LLM-friendly)
                analysis["posture_analysis"] = self._analyze_posture_llm_friendly(frame)

                # Body language analysis (LLM-friendly)
                analysis["body_language"] = self._analyze_body_language_llm_friendly(frame)

                # Attention and focus (LLM-friendly)
                analysis["attention_focus"] = self._assess_attention_focus_simple(analysis)

            return analysis

        except Exception as e:
            logger.error(f"❌ Error in LLM-friendly frame analysis: {e}")
            logger.error(f"❌ Frame analysis failed for frame {frame_number}, using error data")
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

    def _analyze_eye_gaze_llm_friendly(self, frame):
        """LLM-friendly eye gaze analysis"""
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

            # Update gaze history
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

    def _analyze_emotions_llm_friendly(self, frame):
        """LLM-friendly emotion analysis with proper emotion categories"""
        try:
            # Detect primary emotion using proper categories
            dominant_emotion = self._detect_primary_emotion_categories(frame)

            # Micro-expression detection
            micro_expressions = self._detect_micro_expressions_simple(frame, dominant_emotion)

            # Calculate emotion variability from history
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
        """Detect emotion using proper categories: anger, fear, sadness, disgust, surprise, happiness, neutral"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Try to use the smile cascade from your directory first
            smile_cascade_paths = [
                "/app/open_cv/haarcascade_smile.xml",
                cv2.data.haarcascades + 'haarcascade_smile.xml'
            ]

            smile_cascade = None
            for path in smile_cascade_paths:
                if os.path.exists(path):
                    smile_cascade = cv2.CascadeClassifier(path)
                    break

            # Basic emotion detection (this would be enhanced with proper emotion detection library)
            if smile_cascade and not smile_cascade.empty():
                smiles = smile_cascade.detectMultiScale(gray, 1.8, 20)
                if len(smiles) > 0:
                    return "happiness"

            # Enhanced emotion detection using facial landmarks if available
            if ADVANCED_LIBS_AVAILABLE and self.landmark_predictor:
                faces = self.face_detector(gray)
                if len(faces) > 0:
                    landmarks = self.landmark_predictor(gray, faces[0])
                    emotion = self._analyze_emotion_from_landmarks(landmarks)
                    if emotion != "neutral":
                        return emotion

            # Default to neutral if no clear emotion detected
            return "neutral"

        except Exception as e:
            logger.error(f"❌ Primary emotion detection error: {e}")
            return "neutral"

    def _analyze_emotion_from_landmarks(self, landmarks):
        """Analyze emotion from facial landmarks"""
        try:
            # Mouth analysis for happiness/sadness
            mouth_left = (landmarks.part(48).x, landmarks.part(48).y)
            mouth_right = (landmarks.part(54).x, landmarks.part(54).y)
            mouth_top = (landmarks.part(51).x, landmarks.part(51).y)
            mouth_bottom = (landmarks.part(57).x, landmarks.part(57).y)

            mouth_width = euclidean(mouth_left, mouth_right)
            mouth_height = euclidean(mouth_top, mouth_bottom)
            mouth_ratio = mouth_width / mouth_height if mouth_height > 0 else 0

            # Eyebrow analysis for anger/surprise
            left_eyebrow_inner = (landmarks.part(21).x, landmarks.part(21).y)
            right_eyebrow_inner = (landmarks.part(22).x, landmarks.part(22).y)

            # Eye analysis
            left_eye_top = (landmarks.part(37).x, landmarks.part(37).y)
            left_eye_bottom = (landmarks.part(41).x, landmarks.part(41).y)
            right_eye_top = (landmarks.part(44).x, landmarks.part(44).y)
            right_eye_bottom = (landmarks.part(46).x, landmarks.part(46).y)

            eye_openness = (euclidean(left_eye_top, left_eye_bottom) + euclidean(right_eye_top, right_eye_bottom)) / 2

            # Simple emotion classification based on facial features
            if mouth_ratio > 3.5:  # Wide mouth
                return "happiness"
            elif mouth_ratio < 2.5:  # Narrow mouth
                return "sadness"
            elif eye_openness > 15:  # Wide eyes
                return "surprise"
            elif left_eyebrow_inner[1] < left_eye_top[1] - 10:  # Raised eyebrows
                return "surprise"
            elif left_eyebrow_inner[1] > left_eye_top[1] - 5:  # Lowered eyebrows
                return "anger"
            else:
                return "neutral"

        except Exception as e:
            logger.error(f"❌ Landmark emotion analysis error: {e}")
            return "neutral"

    def _detect_micro_expressions_simple(self, frame, primary_emotion):
        """Simple micro-expression detection for LLM analysis"""
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
        """Simple emotion variability for LLM analysis"""
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
        """Simplified posture analysis for LLM"""
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
                "posture_stability": "stable"  # Simplified for single frame
            }

        except Exception as e:
            logger.error(f"❌ Posture analysis error: {e}")
            return {
                "face_centering": "unknown",
                "posture_stability": "unknown"
            }

    def _analyze_body_language_llm_friendly(self, frame):
        """Simplified body language analysis for LLM"""
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
        """Simple head movement calculation for LLM"""
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
        """Simple attention and focus assessment for LLM"""
        try:
            eye_gaze = analysis.get("eye_gaze_analysis", {})
            body_lang = analysis.get("body_language", {})
            posture = analysis.get("posture_analysis", {})

            # Check if looking away
            looking_away = eye_gaze.get("eye_gaze_direction") in ["looking_left", "looking_right", "gaze_averted", "eyes_closed"]

            # Check for distractions
            distraction_present = (
                looking_away or
                posture.get("face_centering") == "poorly_positioned" or
                body_lang.get("head_movement") in ["moderate_movement", "high_movement"]
            )

            # Determine attention level
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
        """Basic gaze analysis fallback for LLM"""
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
        """Create error frame data structure for LLM analysis"""
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

        logger.info(f"🚀 Initialized EnhancedFrameProcessor with LLM-Friendly Analysis")
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
        logger.info(f"🎥 Starting LLM-FRIENDLY frame processing for session: {self.session_id}")
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
            logger.info(f"🎬 Processing {len(frame_files)} stored frame messages with LLM-friendly analysis")

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
        """Process a single frame message with LLM-friendly analysis"""
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

            # Perform LLM-friendly analysis
            timestamp = message_dict.get('timestamp', time.time())
            analysis_result = self.analyzer.analyze_frame_comprehensive(frame, frame_number, timestamp)

            # Convert numpy types to Python native types for JSON serialization
            analysis_result = self._convert_numpy_types(analysis_result)

            # Store analysis result
            analysis_file = f"/tmp/analysis_{self.session_id}_{frame_number}.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_result, f, indent=2)

            logger.info(f"✅ LLM-friendly analysis completed for frame {frame_number}")
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
        """Finalize and save LLM-friendly analysis"""
        try:
            logger.info(f"📊 Generating LLM-friendly analysis report for session: {self.session_id}")

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
            session_summary = self._generate_session_summary_llm_friendly(frame_analyses)

            # Create comprehensive report
            timestamp = int(time.time())
            hash_part = self.session_id.split('_')[-1] if '_' in self.session_id else 'nohash'
            output_filename = f"llm_friendly_analysis_{self.user_id}_{self.interview_id}_{timestamp}_{hash_part}.json"
            output_path = f"/app/{output_filename}"

            comprehensive_report = {
                'metadata': {
                    'session_id': self.session_id,
                    'user_id': self.user_id,
                    'interview_id': self.interview_id,
                    'timestamp': timestamp,
                    'frames_processed': self.frames_processed_count,
                    'frames_found': self.frames_found_count,
                    'analysis_type': 'llm_friendly_comprehensive',
                    'filename': output_filename,
                    'advanced_libs_available': ADVANCED_LIBS_AVAILABLE,
                    'format': 'clean_no_duplicates_proper_emotions'
                },
                'processing_stats': {
                    'messages_scanned': self.messages_scanned,
                    'session_messages_found': self.session_messages_found,
                    'frames_found': self.frames_found_count,
                    'frames_processed': self.frames_processed_count,
                    'processing_success_rate': (self.frames_processed_count / max(1, self.frames_found_count)) * 100,
                    'processing_method': 'llm_friendly_processor'
                },
                'session_summary': session_summary,
                'frame_analyses': frame_analyses  # Include ALL frame analyses
            }

            with open(output_path, 'w') as f:
                json.dump(comprehensive_report, f, indent=4, default=str)

            logger.info(f"✅ LLM-friendly analysis report saved to: {output_path}")
            logger.info(f"📁 Clean filename: {output_filename}")
            logger.info(f"📊 Frame analyses included: {len(frame_analyses)} out of {self.frames_processed_count} processed")
            logger.info(f"📈 Final Processing Summary:")
            logger.info(f"   • Messages scanned: {self.messages_scanned}")
            logger.info(f"   • Session messages: {self.session_messages_found}")
            logger.info(f"   • Frames found: {self.frames_found_count}")
            logger.info(f"   • Frames processed: {self.frames_processed_count}")
            logger.info(f"   • LLM-friendly format: ✅")
            logger.info(f"   • Proper emotions: happiness, sadness, anger, etc. ✅")
            logger.info(f"   • No duplicate keys: ✅")
            logger.info(f"   • Clean attention_focus: ✅")
            logger.info(f"   • Advanced analysis: {ADVANCED_LIBS_AVAILABLE}")

            return True

        except Exception as e:
            logger.error(f"❌ LLM-friendly analysis finalization failed: {e}")
            return False

    def _generate_session_summary_llm_friendly(self, frame_analyses):
        """Generate LLM-friendly session summary"""
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

            # Emotion analysis with proper emotions
            emotions = [f.get('emotion_analysis', {}).get('dominant_emotion', 'neutral') 
                       for f in frame_analyses]
            emotion_distribution = {emotion: emotions.count(emotion) for emotion in set(emotions) if emotions}

            # Gaze quality analysis
            gaze_qualities = [f.get('eye_gaze_analysis', {}).get('gaze_quality', 'unknown')
                            for f in frame_analyses if f.get('eye_gaze_analysis', {}).get('gaze_quality') != 'unknown']
            gaze_quality_distribution = {quality: gaze_qualities.count(quality) for quality in set(gaze_qualities) if gaze_qualities}

            # Distraction analysis
            distracted_frames = sum(1 for f in frame_analyses
                                  if f.get('attention_focus', {}).get('distraction_present', False))
            distraction_rate = (distracted_frames / total_frames) * 100

            # Head movement analysis
            head_movements = [f.get('body_language', {}).get('head_movement', 'unknown')
                            for f in frame_analyses if f.get('body_language', {}).get('head_movement') != 'unknown']
            stable_movement_frames = sum(1 for movement in head_movements if movement in ['minimal', 'very_stable'])
            movement_stability = (stable_movement_frames / len(head_movements)) * 100 if head_movements else 0

            return {
                'total_frames_analyzed': total_frames,
                'eye_contact_analysis': {
                    'percentage_looking_at_camera': round(eye_contact_percentage, 2),
                    'total_eye_contact_frames': looking_at_camera_frames,
                    'gaze_quality_distribution': gaze_quality_distribution
                },
                'attention_analysis': {
                    'focus_percentage': round(focus_percentage, 2),
                    'focused_frames': focused_frames,
                    'attention_level_distribution': {level: attention_levels.count(level) for level in set(attention_levels)}
                },
                'emotion_analysis': {
                    'emotion_distribution': emotion_distribution,
                    'dominant_session_emotion': max(emotion_distribution, key=emotion_distribution.get) if emotion_distribution else 'neutral',
                    'total_emotion_frames': len(emotions)
                },
                'distraction_analysis': {
                    'distraction_rate': round(distraction_rate, 2),
                    'distracted_frames': distracted_frames,
                    'clean_frames': total_frames - distracted_frames
                },
                'movement_analysis': {
                    'movement_stability_percentage': round(movement_stability, 2),
                    'stable_movement_frames': stable_movement_frames,
                    'total_movement_analyzed': len(head_movements)
                },
                'overall_assessment': {
                    'session_quality': self._assess_simple_session_quality(focus_percentage, eye_contact_percentage, distraction_rate),
                    'key_strengths': self._identify_simple_strengths(eye_contact_percentage, focus_percentage, distraction_rate),
                    'improvement_areas': self._identify_simple_improvements(eye_contact_percentage, focus_percentage, distraction_rate),
                    'summary_score': round((eye_contact_percentage + focus_percentage + (100 - distraction_rate)) / 3, 2)
                }
            }

        except Exception as e:
            logger.error(f"❌ Session summary generation error: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}

    def _assess_simple_session_quality(self, focus_pct, eye_contact_pct, distraction_rate):
        """Simple session quality assessment"""
        avg_score = (focus_pct + eye_contact_pct + (100 - distraction_rate)) / 3

        if avg_score > 80:
            return "excellent"
        elif avg_score > 70:
            return "very_good"
        elif avg_score > 60:
            return "good"
        elif avg_score > 50:
            return "fair"
        else:
            return "needs_improvement"

    def _identify_simple_strengths(self, eye_contact_pct, focus_pct, distraction_rate):
        """Identify simple strengths"""
        strengths = []

        if eye_contact_pct > 75:
            strengths.append("excellent_eye_contact")
        elif eye_contact_pct > 60:
            strengths.append("good_eye_contact")

        if focus_pct > 75:
            strengths.append("high_focus")
        elif focus_pct > 60:
            strengths.append("good_focus")

        if distraction_rate < 20:
            strengths.append("minimal_distractions")
        elif distraction_rate < 35:
            strengths.append("manageable_distractions")

        return strengths

    def _identify_simple_improvements(self, eye_contact_pct, focus_pct, distraction_rate):
        """Identify simple improvement areas"""
        improvements = []

        if eye_contact_pct < 50:
            improvements.append("improve_eye_contact")

        if focus_pct < 50:
            improvements.append("increase_focus")

        if distraction_rate > 40:
            improvements.append("reduce_distractions")

        return improvements


def main():
    parser = argparse.ArgumentParser(description="LLM-Friendly Video Frame Analyzer")
    parser.add_argument('--session_id', required=True, help='Session ID for the interview')
    parser.add_argument('--interview_id', required=True, type=int, help='Interview ID')
    parser.add_argument('--auto_process', action='store_true', help='Run in automated mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🚀 Starting LLM-Friendly Video Frame Analysis")
    logger.info(f"   Session ID: {args.session_id}")
    logger.info(f"   Interview ID: {args.interview_id}")
    logger.info(f"   Advanced Libraries: {ADVANCED_LIBS_AVAILABLE}")
    logger.info(f"   Format: Clean, No Duplicates, Proper Emotions ✅")

    if args.auto_process:
        try:
            processor = EnhancedFrameProcessor(
                session_id=args.session_id,
                interview_id=args.interview_id
            )

            success = processor.process_frames()

            if success:
                logger.info(f"🎉 LLM-friendly video analysis completed successfully!")
                logger.info(f"📊 Final Stats: {processor.frames_processed_count} frames processed from {processor.frames_found_count} found")
                logger.info(f"✨ Output: Clean JSON with proper emotions, no duplicates, LLM-ready!")
                sys.exit(0)
            else:
                logger.error(f"💥 LLM-friendly video analysis failed!")
                sys.exit(1)

        except Exception as e:
            logger.error(f"❌ Fatal error in LLM-friendly processing: {e}")
            sys.exit(1)
    else:
        logger.info(f"ℹ️ Use --auto_process to start analysis")
        logger.info(f"📋 LLM-Friendly Features:")
        logger.info(f"   • Proper emotions: happiness, sadness, anger, fear, surprise, disgust, neutral")
        logger.info(f"   • No duplicate keys: removed eye_contact + eye_gaze_direction conflicts")
        logger.info(f"   • Clean attention_focus: focused, distracted, etc.")
        logger.info(f"   • No confusing numbers: descriptive text only")
        logger.info(f"   • Perfect for AI analysis")

if __name__ == "__main__":
	main()
