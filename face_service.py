import cv2
import numpy as np
from deepface import DeepFace
from scipy.spatial.distance import cosine
import logging

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self):
        self.model_name = "Facenet512"
        self.threshold = 0.4  # Stricter threshold for 512 dim

    def generate_embedding(self, image_bytes):
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Could not decode image")
                return None

            # DeepFace expects path or numpy array
            results = DeepFace.represent(
                img_path=img, 
                model_name=self.model_name, 
                enforce_detection=True,
                detector_backend="opencv" # Faster than mtcnn/retinaface for simple cases, but less accurate. 
                                          # Use 'mediapipe' or 'mtcnn' for better results if installed.
            )
            
            if not results:
                return None
            
            # Return the first face found
            return results[0]["embedding"]
        except Exception as e:
            logger.error(f"Error in face representation: {e}")
            return None

    def match_face(self, target_embedding, all_students):
        best_match = None
        min_distance = float("inf")

        for student in all_students:
            if "face_embedding" not in student or not student["face_embedding"]:
                continue
            
            db_embedding = student["face_embedding"]
            dist = cosine(target_embedding, db_embedding)
            
            if dist < self.threshold and dist < min_distance:
                min_distance = dist
                best_match = student
        
        return best_match, min_distance

face_service = FaceService()
