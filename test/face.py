import cv2
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model
model = load_model('model.h5')


face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

emotionMapping = {
    0: "angry",
    1: "disgust",
    2: "fear",
    3: "happy",
    4: "neutral",
    5: "sad",
    6: "surprise",
}

image = cv2.imread('yt.png')
h, w, _ = image.shape
print(h)
print(w)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

x, y, w, h = faces[0]
print(w)
cropped = image[y:y+h, x:x+w]
# print(cropped)
# print(cropped.shape)
    
# print(type(cropped))

def preprocess(image_array):
    image_array = image_array / 255.0
    image_array = np.expand_dims(image_array, axis=0)
    return image_array

def predict(image_matrix):
    # image_array = np.array(image_matrix.matrix, dtype=np.float32)
    # image_array = np.clip(image_array * 255.0, 0, 255).astype(np.uint8)

    image = Image.fromarray(image_matrix)
    # print(image_array.shape)

    image = image.resize((48, 48))

    resized_array = np.array(image)

    processed_image = preprocess(resized_array)
    prediction = model.predict(processed_image)
    predicted_class_index = int(np.argmax(prediction, axis=1)[0])
    return emotionMapping.get(predicted_class_index)

print(predict(cropped))