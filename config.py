import pymongo
import google.generativeai as genai
import cv2
import mediapipe as mp
import speech_recognition as sr
import os

client = pymongo.MongoClient(os.getenv('MONGO_CONN_URL'))

db = client.compfest

userCollection = db["user"]
vacancyCollection = db["vacancy"]
questionCollection = db["question"]
frameCollection = db["frame"]
audioCollection = db["audio"]

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

recognizer = sr.Recognizer()
faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
mpHands = mp.solutions.hands
modelHand = mpHands.Hands()