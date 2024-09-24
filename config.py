import pymongo
import google.generativeai as genai
import cv2
import mediapipe as mp
import speech_recognition as sr

client = pymongo.MongoClient('mongodb+srv://mutawallynawwar:7WAjgvIb4egLmTEV@cluster0.mrgy4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

db = client.compfest

userCollection = db["user"]
vacancyCollection = db["vacancy"]
questionCollection = db["question"]
frameCollection = db["frame"]
audioCollection = db["audio"]

genai.configure(api_key="AIzaSyDA501iLj4OCrNy-A1aFlXpxo81cMKkqCY")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

recognizer = sr.Recognizer()
faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
mpHands = mp.solutions.hands
modelHand = mpHands.Hands()