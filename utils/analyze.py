import cv2
from config import audioCollection, frameCollection, questionCollection
import os
from const import UPLOAD_DIRECTORY
from moviepy.editor import VideoFileClip, AudioFileClip
import numpy as np
import librosa
import httpx
import speech_recognition as sr
import math
from config import modelHand, faceCascade, recognizer, mpDrawing, mpHands, bucket
async def analyze(video_location, email, uuid):
    try:
        question = questionCollection.find_one({"id": uuid})

        print("read video start")
        video_capture = cv2.VideoCapture(video_location)
        audio_location = UPLOAD_DIRECTORY / f"{uuid}.wav"
        videoFile = VideoFileClip(str(video_location))
        audioFile = videoFile.audio
        if audioFile == None:
            print("Your video doesn't have audio")
            raise Exception("Your video doesn't have audio")
        audioFile.write_audiofile(str(audio_location))
        audioFile.close()
        videoFile.close()

        frames = []

        if not video_capture.isOpened():
            raise Exception("failed to read video")

        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        # frame_interval = int(fps / 6)
        print("read video done")
        messages = question["messages"]
        messages.append("read video done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print("frame start")
        frame_count = 0
        while True:
            success, frame = video_capture.read()

            if not success:
                break 

            # if frame_count % frame_interval == 0:
            #     frames.append(frame)
            frames.append(frame)

            frame_count += 1

        video_capture.release()


        print("frame done")
        messages = question["messages"]
        messages.append("frame done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print(f"frame length: {len(frames)}")
        print("emotions start")
        emotions, frames = await analyze_emotions(frames)
        print("emotions done")
        messages = question["messages"]
        messages.append("emotions done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print("hand start")
        handsResult, frames = await analyze_hands(frames)
        print("hand done")
        messages = question["messages"]
        messages.append("hand done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print("upload gcs start")
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        new_video_location = str(video_location).split(".")[0] + ".avi"
        out = cv2.VideoWriter(new_video_location, fourcc, fps, (frame_width, frame_height))
        for frame in frames:
            out.write(frame)
        out.release()
        
        newVideo = VideoFileClip(str(new_video_location))
        newAudio = AudioFileClip(str(audio_location)).set_duration(newVideo.duration)
        newVideo = newVideo.set_audio(newAudio)
        newVideo.write_videofile(str(video_location), codec='libx264', audio_codec='aac')
        newVideo.close()
        newAudio.close()
        blob = bucket.blob(str(video_location))
        blob.upload_from_filename(str(video_location))
        print("upload gcs done")
        messages = question["messages"]
        messages.append("gcs upload done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print("translate start")
        audio_file = sr.AudioFile(str(audio_location))
        with audio_file as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="id-ID")
        print("translate done")
        messages = question["messages"]
        messages.append("translate done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})


        print("snr start")
        audio, ser = librosa.load(str(audio_location), sr=None)
        snr_values = compute_snr(audio, ser)
        arr_cleaned = np.nan_to_num(snr_values, nan=0.0)
        print("snr done")
        messages = question["messages"]
        messages.append("snr done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages}})

        print("mongo function")
        frameCollection.insert_one({"id": uuid, "email": email, "emotions": emotions, "hands": handsResult})
        audioCollection.insert_one({"id": uuid, "email": email, "snr": arr_cleaned.tolist(), "answer": text})
        messages = question["messages"]
        messages.append("all done")
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages, "status": "SUCCESS", "answer": text}})


        os.remove(video_location)
        os.remove(new_video_location)
        os.remove(audio_location)
        print("all done")
    except Exception as e:
        print(e)
        messages = question["messages"]
        messages.append(str(e))
        question["messages"] = messages        
        questionCollection.find_one_and_update({"id": uuid},{ "$set": { "messages": messages, "status": "ERROR"}})

async def analyze_emotions(frames):
    emotions = []
    for index, frame in enumerate(frames):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            x, y, w, h = faces[0]
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cropped = frame[y:y+h, x:x+w]

            currEmotion = ""
            if(index % 1000 == 0):
                async with httpx.AsyncClient() as client:
                    response = await client.post(os.getenv('API_EMOTION_URL'), json={ "matrix": cropped.tolist()})
                    response.raise_for_status()
                    data = response.json()
                    currEmotion = data["prediction"]
                print(index)
            emotions.append(currEmotion)
        else:
            emotions.append(-1)
    
    return emotions, frames

async def analyze_hands(frames):
    handsPositionX = []
    handsPositionY = []
    for frame in frames:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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

            for hand_landmarks in hands.multi_hand_landmarks:
                mpDrawing.draw_landmarks(
                    frame, 
                    hand_landmarks,
                    mpHands.HAND_CONNECTIONS,
                    mpDrawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mpDrawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
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

    return handsResult, frames

def compute_snr(audio, sr, frame_length=1024, hop_length=512):
    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    power_spec = np.abs(stft)**2
    signal_power = np.mean(power_spec, axis=0)
    noise_power = np.median(power_spec, axis=0)
    snr = 10 * np.log10(signal_power / noise_power)
    
    return snr