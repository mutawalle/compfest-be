import speech_recognition as sr
from google.cloud import speech_v1p1beta1 as speech
import io
import os
import wave
import dotenv
import google.generativeai as genai
import json


dotenv.load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

def get_sample_rate(wav_file):
    with wave.open(wav_file, 'rb') as wav:
        sample_rate = wav.getframerate()
        return sample_rate

sample_rate = get_sample_rate('tes2.wav')
print(sample_rate)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "compfest-434318-00fa3dec41ec.json"


def transcribe_speech_with_timestamps(speech_file):
    client = speech.SpeechClient()

    with io.open(speech_file, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code="id-ID",
        enable_word_time_offsets=True,  # Enable timestamps
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    result = operation.result(timeout=500)
    print(result.results[0].alternatives[0].transcript)
#     for word_info in response.results[0].alternatives[0].words:
#         word = word_info.word
#         start_time = word_info.start_time.total_seconds()
#         end_time = word_info.end_time.total_seconds()
#         print(f"{word}  {start_time}   {end_time}")
        
#     prompt = """
#                 Split the following text by phrases. Provide an emotion angry/disgust/fear/happy/neutral/sad/surprise for each phrase and indicate whether hand gestures are needed when delivering it. 
#                 Here is the text: {transcript}. 
#                 Provide the format as an array: [{{"phrase": "text", "emotion": "angry/disgust/fear/happy/neutral/sad/surprise", "gesture": true/false}}]. 
#                 Return it as an array without any additional characters or formatting such as ```json``` or backticks.
#             """
    
#     formatted = prompt.format(transcript=response.results[0].alternatives[0].transcript)

#     # print(formatted)

#     resGemini = model.generate_content([formatted])

#     object = json.loads(resGemini.text)

#     phraseIndex = 0
#     for word_info in response.results[0].alternatives[0].words:
#         word = word_info.word
#         start_time = word_info.start_time.total_seconds()
#         end_time = word_info.end_time.total_seconds()
#         for i in range(phraseIndex, len(object)):
#             if word.lower() in object[phraseIndex]["phrase"].lower():
#                 if "start_time" not in object[phraseIndex]:
#                     object[phraseIndex]["start_time"] = start_time
#                 object[phraseIndex]["end_time"] = end_time
#                 break
#             else:
#                 phraseIndex += 1

#     print(object)

    

transcribe_speech_with_timestamps("tes2.wav")
