import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image

class ComputerVisionAnalyzer:
    def __init__(self):
        # Load pre-trained models
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    def analyze_frames(self, frames):
        """Analyze video frames for cheating detection"""
        results = {
            'face_detection': [],
            'eye_movement': [],
            'head_movement': [],
            'multiple_faces_detected': False,
            'suspicious_activity_count': 0,
            'cheating_detected': False,
            'cheating_confidence': 0.0
        }
        
        previous_face_center = None
        face_absent_count = 0
        multiple_faces_count = 0
        
        for i, frame_data in enumerate(frames):
            try:
                # Decode base64 frame
                frame = self.decode_frame(frame_data)
                if frame is None:
                    continue
                
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                
                frame_analysis = {
                    'frame_index': i,
                    'faces_detected': len(faces),
                    'face_positions': faces.tolist() if len(faces) > 0 else [],
                    'suspicious': False
                }
                
                if len(faces) == 0:
                    face_absent_count += 1
                    frame_analysis['suspicious'] = True
                    frame_analysis['reason'] = 'No face detected'
                elif len(faces) > 1:
                    multiple_faces_count += 1
                    frame_analysis['suspicious'] = True
                    frame_analysis['reason'] = 'Multiple faces detected'
                    results['multiple_faces_detected'] = True
                else:
                    # Single face detected - analyze movement
                    face = faces[0]
                    face_center = (face[0] + face[2]//2, face[1] + face[3]//2)
                    
                    if previous_face_center is not None:
                        movement = np.sqrt((face_center[0] - previous_face_center[0])**2 + 
                                         (face_center[1] - previous_face_center[1])**2)
                        
                        # Detect excessive head movement
                        if movement > 50:  # Threshold for suspicious movement
                            frame_analysis['suspicious'] = True
                            frame_analysis['reason'] = 'Excessive head movement'
                            frame_analysis['movement_distance'] = float(movement)
                    
                    previous_face_center = face_center
                    
                    # Analyze eye movement
                    face_roi = gray[face[1]:face[1]+face[3], face[0]:face[0]+face[2]]
                    eyes = self.eye_cascade.detectMultiScale(face_roi)
                    frame_analysis['eyes_detected'] = len(eyes)
                    
                    if len(eyes) < 2:
                        frame_analysis['suspicious'] = True
                        frame_analysis['reason'] = 'Eyes not properly detected'
                
                results['face_detection'].append(frame_analysis)
                
                if frame_analysis['suspicious']:
                    results['suspicious_activity_count'] += 1
                
            except Exception as e:
                print(f"Error analyzing frame {i}: {e}")
                continue
        
        # Calculate cheating confidence
        total_frames = len(frames)
        if total_frames > 0:
            suspicious_ratio = results['suspicious_activity_count'] / total_frames
            results['cheating_confidence'] = min(suspicious_ratio * 100, 100)
            results['cheating_detected'] = suspicious_ratio > 0.3  # 30% threshold
        
        # Add summary statistics
        results['summary'] = {
            'total_frames_analyzed': total_frames,
            'face_absent_frames': face_absent_count,
            'multiple_faces_frames': multiple_faces_count,
            'suspicious_activity_ratio': results['suspicious_activity_count'] / max(total_frames, 1)
        }
        
        return results
    
    def decode_frame(self, frame_data):
        """Decode base64 frame data to OpenCV format"""
        try:
            # Remove data URL prefix if present
            if frame_data.startswith('data:image'):
                frame_data = frame_data.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(frame_data)
            
            # Convert to PIL Image
            pil_image = Image.open(BytesIO(image_data))
            
            # Convert to OpenCV format
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            return opencv_image
            
        except Exception as e:
            print(f"Error decoding frame: {e}")
            return None
