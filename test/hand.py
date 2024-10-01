import cv2
import mediapipe as mp

# Initialize MediaPipe Hands module
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_drawing = mp.solutions.drawing_utils

image = cv2.imread('yt.png')
rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
results = hands.process(rgb_frame)

# Draw hand landmarks
# if results.multi_hand_landmarks:
#     for index, landmarks in enumerate(results.multi_hand_landmarks):
#         print(landmarks)
#         # if index > 4 and index < 9:
#         mp_drawing.draw_landmarks(image, landmarks, mp_hands.HAND_CONNECTIONS)

print(results.multi_hand_landmarks[0].landmark[8].x)

cv2.imwrite("output.jpg", image)