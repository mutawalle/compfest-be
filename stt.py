import speech_recognition as sr

from const import UPLOAD_DIRECTORY
from moviepy.editor import VideoFileClip

audio_location = UPLOAD_DIRECTORY / f"tes.wav"
videoFile = VideoFileClip(str("youtube2.mp4"))
audioFile = videoFile.audio
if audioFile == None:
    print("Your video doesn't have audio")
audioFile.write_audiofile(str(audio_location))

print(audio_location)
# Initialize recognizer
recognizer = sr.Recognizer()

# Load the audio file
audio_file = sr.AudioFile(str(audio_location))  # Replace with your file path

with audio_file as source:
    audio = recognizer.record(source)

try:
    text = recognizer.recognize_google(audio, language="id-ID")
    print("Transcription: ", text)
except sr.UnknownValueError:
    print("Google Speech Recognition could not understand audio")
except sr.RequestError as e:
    print(f"Could not request results from Google Speech Recognition service; {e}")


