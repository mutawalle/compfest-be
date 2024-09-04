import cv2
from bson.binary import Binary
from config import audioCollection, frameCollection, userCollection
import os
from const import UPLOAD_DIRECTORY
from moviepy.editor import VideoFileClip
import numpy as np
import librosa
import httpx
import mediapipe as mp
import speech_recognition as sr
import math

recognizer = sr.Recognizer()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
mp_hands = mp.solutions.hands
modelHand = mp_hands.Hands()

async def readVideo(video_location, decoded_token, uuid):
    try:
        video_capture = cv2.VideoCapture(video_location)

        frames = []

        if not video_capture.isOpened():
            print("Error: Could not open video.")
            return frames

        fps = video_capture.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / 6)

        print("frame start")
        frame_count = 0
        while True:
            success, frame = video_capture.read()

            if not success:
                break 

            if frame_count % frame_interval == 0:
                frames.append(frame)

            frame_count += 1

        video_capture.release()
        print("frame done")

        print(f"frame length: {len(frames)}")
        print("emotions start")
        emotions = []
        handsPositionX = []
        handsPositionY = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(faces) > 0:
                x, y, w, h = faces[0]
                cropped = frame[y:y+h, x:x+w]
                async with httpx.AsyncClient() as client:
                    response = await client.post("http://localhost:7861/predict", json={ "matrix": cropped.tolist()})
                    response.raise_for_status()
                    data = response.json()
                    emotions.append(data["prediction"])
            else:
                emotions.append(-1)

        print("emotions done")

        print("hand start")
        for frame in frames:
            hands = modelHand.process(rgb_frame)
            if hands.multi_hand_landmarks:
                first_hand = hands.multi_hand_landmarks[0]
                if len(hands.multi_hand_landmarks) == 1:
                    handsPositionX.append(first_hand.landmark[0].x)
                    handsPositionY.append(first_hand.landmark[0].y)
                else:
                    second_hand = hands.multi_hand_landmarks[1]
                    handsPositionX.append((first_hand.landmark[0].x + second_hand.landmark[0].x)/2)
                    handsPositionY.append((first_hand.landmark[0].y + second_hand.landmark[0].y)/2)
            else:
                handsPositionX.append(-1)
                handsPositionY.append(-1)
        handsPositionXnp = np.array(handsPositionX)
        handsPositionXnp = np.diff(handsPositionXnp)
        handsPositionYnp = np.array(handsPositionY)
        handsPositionYnp = np.diff(handsPositionYnp)
        handsPositionXnp = handsPositionXnp.tolist()
        handsPositionYnp = handsPositionYnp.tolist()
        handsResult = []
        for i in range(len(handsPositionXnp)):
            handsResult.append(math.sqrt(handsPositionXnp[i]**2 + handsPositionYnp[i]**2))
        print("hand done")

        # frames_binary = []
        # for frame in frames:
        #     _, buffer = cv2.imencode('.jpg', frame)
        #     frames_binary.append(Binary(buffer.tobytes()))

        audio_location = UPLOAD_DIRECTORY / f"{uuid}.wav"
        videoFile = VideoFileClip(str(video_location))
        audioFile = videoFile.audio
        if audioFile == None:
            print("Your video doesn't have audio")
            raise Exception
        audioFile.write_audiofile(str(audio_location))
        audioFile.close()
        videoFile.close()

        print("translate start")
        audio_file = sr.AudioFile(str(audio_location))

        with audio_file as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="id-ID")
        print("translate done")
        print("snr start")
        audio, ser = librosa.load(str(audio_location), sr=None)

        snr_values = compute_snr(audio, ser)
        arr_cleaned = np.nan_to_num(snr_values, nan=0.0)
        print("snr done")

        print("mongo function")
        # for frame in frames_binary:
        frameCollection.insert_one({"id": uuid, "email": decoded_token["email"], "emotions": emotions, "hands": handsResult})
        audioCollection.insert_one({"id": uuid, "email": decoded_token["email"], "snr": arr_cleaned.tolist(), "answer": text})
        user = userCollection.find_one({"email": decoded_token["email"]})
        videos = user["videos"]
        for video in videos:
            if video["id"] == uuid:
                video["status"] = "SUCCESS"
        
        userCollection.find_one_and_update({"email": decoded_token["email"]},{ "$set": { "videos": videos}})

        os.remove(video_location)
        os.remove(audio_location)
        print("all done")
    except Exception as e:
        print(e)
        user = userCollection.find_one({"email": decoded_token["email"]})
        videos = user["videos"]
        for video in videos:
            if video["id"] == uuid:
                video["status"] = "ERROR"
        
        userCollection.find_one_and_update({"email": decoded_token["email"]},{ "$set": { "videos": videos}})



def compute_snr(audio, sr, frame_length=1024, hop_length=512):
    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    power_spec = np.abs(stft)**2
    signal_power = np.mean(power_spec, axis=0)
    noise_power = np.median(power_spec, axis=0)
    snr = 10 * np.log10(signal_power / noise_power)
    
    return snr