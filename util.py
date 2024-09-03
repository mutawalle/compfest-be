import cv2
from bson.binary import Binary
from config import audioCollection, frameCollection, userCollection
import os
from const import UPLOAD_DIRECTORY
from moviepy.editor import VideoFileClip
import uuid
import numpy as np
import librosa

def readVideo(video_location, decoded_token):
    video_capture = cv2.VideoCapture(video_location)

    frames = []

    if not video_capture.isOpened():
        print("Error: Could not open video.")
        return frames

    fps = video_capture.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps / 4)

    frame_count = 0
    while True:
        success, frame = video_capture.read()

        if not success:
            break 

        if frame_count % frame_interval == 0:
            frames.append(frame)

        frame_count += 1

    video_capture.release()

    print("frame start")
    frames_binary = []
    for frame in frames:
        _, buffer = cv2.imencode('.jpg', frame)
        frames_binary.append(Binary(buffer.tobytes()))
    print("frame done")

    audio_location = UPLOAD_DIRECTORY / f"{uuid.uuid4()}.wav"
    print(audio_location)
    videoFile = VideoFileClip(str(video_location))
    print(videoFile)
    audioFile = videoFile.audio
    print(audioFile)
    if audioFile == None:
        print("Your video doesn't have audio")
    audioFile.write_audiofile(str(audio_location))
    audioFile.close()
    videoFile.close()

    audio, sr = librosa.load(str(audio_location), sr=None)

    print("snr start")
    snr_values = compute_snr(audio, sr)
    print("snr done")

    snr_binary = Binary(snr_values.tobytes())
    try:
        audioCollection.delete_many({"email": decoded_token["email"]})
        frameCollection.delete_many({"email": decoded_token["email"]})
        for frame in frames_binary:
            frameCollection.insert_one({"email": decoded_token["email"], "frame": frame})
        audioCollection.insert_one({"email": decoded_token["email"], "audio": snr_binary, "shape": snr_values.shape, "dtype": str(snr_values.dtype)})
        userCollection.find_one_and_update({"email": decoded_token["email"]}, {"$set": { "status": "READ"}})
    except Exception as e:
        print(e)

    os.remove(video_location)
    os.remove(audio_location)
    print("all done")


def compute_snr(audio, sr, frame_length=1024, hop_length=512):
    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    power_spec = np.abs(stft)**2
    signal_power = np.mean(power_spec, axis=0)
    noise_power = np.median(power_spec, axis=0)
    snr = 10 * np.log10(signal_power / noise_power)
    
    return snr