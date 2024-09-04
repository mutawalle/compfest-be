import cv2
import mediapipe as mp

# Initialize MediaPipe Hands module
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_drawing = mp.solutions.drawing_utils

image = cv2.imread('youtube.png')
rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
results = hands.process(rgb_frame)

# Draw hand landmarks
if results.multi_hand_landmarks:
    for landmarks in results.multi_hand_landmarks:
        print(landmarks)
        mp_drawing.draw_landmarks(image, landmarks, mp_hands.HAND_CONNECTIONS)

cv2.imwrite("output.jpg", image)