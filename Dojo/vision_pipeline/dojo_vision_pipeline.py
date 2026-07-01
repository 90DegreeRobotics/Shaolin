# SUPERSEDED (2026-06-30): this early prototype has been refactored into the
# chirox package, which splits pure geometry from the camera loop so the reflex
# is unit-testable and adds an explicit uncertainty gate:
#   - chirox/vision/stances.py   (pure, tested geometry — Ma Bu + Gong Bu)
#   - chirox/vision/pipeline.py  (webcam/video runner)
#   - chirox/vision/schema.py    (deterministic session summary)
#   - chirox/vision/multicam.py  (front/side fusion for the Weatherman rig)
# Run the current reflex with:  python -m chirox.cli vision --source 0
# This file is kept for history and is no longer the maintained path.

import cv2
import mediapipe as mp
import numpy as np
import json
import time

class DojoVision:
    def __init__(self, camera_index=0):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=1 # 0, 1, or 2 (higher is more accurate but slower)
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.cap = cv2.VideoCapture(camera_index)
        
    def calculate_angle(self, a, b, c):
        """
        Calculate the angle between three points.
        a, b, c are tuples or lists: (x, y)
        b is the vertex.
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle

    def evaluate_horse_stance(self, landmarks):
        """
        Evaluates the Horse Stance (Ma Bu) based on knee and hip angles.
        Returns a dictionary of metrics and a qualitative assessment.
        """
        # Get coordinates
        # Left side
        l_hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
        l_knee = [landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        l_ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        l_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        
        # Right side
        r_hip = [landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        r_knee = [landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        r_ankle = [landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        r_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]

        # Calculate Angles
        l_knee_angle = self.calculate_angle(l_hip, l_knee, l_ankle)
        r_knee_angle = self.calculate_angle(r_hip, r_knee, r_ankle)
        
        l_back_angle = self.calculate_angle(l_shoulder, l_hip, l_knee)
        r_back_angle = self.calculate_angle(r_shoulder, r_hip, r_knee)

        metrics = {
            "left_knee_angle": round(l_knee_angle, 2),
            "right_knee_angle": round(r_knee_angle, 2),
            "left_back_angle": round(l_back_angle, 2),
            "right_back_angle": round(r_back_angle, 2)
        }

        # Stance logic (Ideal horse stance: knees ~90-100 deg, back straight ~170-180 deg)
        warnings = []
        if l_knee_angle > 120 or r_knee_angle > 120:
            warnings.append("Stance is too high. Lower your center of gravity.")
        elif l_knee_angle < 80 or r_knee_angle < 80:
            warnings.append("Stance is too low or collapsing. Maintain structural integrity.")

        if l_back_angle < 150 or r_back_angle < 150:
            warnings.append("Back is slouching. Straighten your posture like a pine tree.")

        assessment = "Stable and rooted." if not warnings else " | ".join(warnings)

        return metrics, assessment

    def run(self):
        print("Starting Dojo Vision Pipeline...")
        print("Press 'q' to quit.")
        
        last_log_time = time.time()
        
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame.")
                break

            # Recolor image to RGB for MediaPipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            
            # Make detection
            results = self.pose.process(image)
            
            # Recolor back to BGR for OpenCV display
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:
                # Render detections
                self.mp_drawing.draw_landmarks(
                    image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                    self.mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2) 
                )
                
                # Evaluate Stance
                metrics, assessment = self.evaluate_horse_stance(results.pose_landmarks.landmark)
                
                # Overlay data
                cv2.putText(image, f"L Knee: {metrics['left_knee_angle']}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(image, f"R Knee: {metrics['right_knee_angle']}", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Print to console every 2 seconds to simulate data feed to LLM
                current_time = time.time()
                if current_time - last_log_time > 2.0:
                    payload = {
                        "timestamp": current_time,
                        "stance": "Horse Stance (Ma Bu)",
                        "metrics": metrics,
                        "assessment_flags": assessment
                    }
                    print(json.dumps(payload))
                    last_log_time = current_time

            cv2.imshow('Dojo Vision (Chan Wu Yi)', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # In a real integration, camera_index would map to the OBS Virtual Camera
    # or the direct Logitech C920 feed (e.g. 0, 1, or 2).
    dojo = DojoVision(camera_index=0)
    dojo.run()
