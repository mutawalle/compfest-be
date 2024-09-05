from fastapi import FastAPI, HTTPException, status, Request, File, UploadFile, BackgroundTasks, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import datetime
import jwt
from config import userCollection, frameCollection, audioCollection, vacancyCollection, questionCollection
from const import UPLOAD_DIRECTORY
from util import readVideo
import numpy as np
import uuid
from pathlib import Path
import os
import google.generativeai as genai
import json
import pdfplumber
from io import BytesIO


app = FastAPI()
genai.configure(api_key="AIzaSyDA501iLj4OCrNy-A1aFlXpxo81cMKkqCY")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.url.path not in ["/login", "/"]:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
            if decoded_token["exp"] < 300:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    response = await call_next(request)
    return response

@app.get("/")
def hello():
    return "Hello World"

@app.get("/login")
async def login(request: Request):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        user = userCollection.find_one({"email": decoded_token["email"]})
        if not user:
            new_user = {"email": decoded_token["email"], "videos": [], "created_at": datetime.datetime.now()}
            userCollection.insert_one(new_user)
            return {"message": "New user created"}
        return decoded_token
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")

@app.get("/reset")
async def reset(request: Request):
    try:
       frameCollection.delete_many({})
       audioCollection.delete_many({})
       questionCollection.delete_many({})
       vacancyCollection.delete_many({})
       return {"message": "OK"}
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.delete("/delete-all-files/")
async def delete_all_files():

    video_extensions = [".mp4", ".avi"] 
    audio_extensions = [".wav", ".mp3"] 
    deleted_files = []

    for file in os.listdir(UPLOAD_DIRECTORY):
        file_path = UPLOAD_DIRECTORY / file
        if file_path.is_file() and (any(file.endswith(ext) for ext in video_extensions) or any(file.endswith(ext) for ext in audio_extensions)):
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
    
    if len(deleted_files) == 0:
        return {"message": "No video or audio files were deleted. No matching files found."}
    
    return {"message": f"Deleted files: {deleted_files}"}
    
@app.post("/vacancy")
async def add_vacancy(request: Request, body = Body(...)):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
            newUuidVacancy = uuid.uuid4().hex
            vacancyCollection.insert_one({
                "id": newUuidVacancy,
                "email": decoded_token["email"],
                "title": body["title"],
                "description": body["description"]
            })
            prompt = 'Berikut merupakan deskripsi sebuah lowongan pekerjaan. posisi: ' + body["title"] + ' deskripsi: ' + body["description"] + '. Bisakah kamu memberikan beberapa pertanyaan yang mungkin digunakan dalam sesi wawancara. Tolong berikan jawaban dalam format JSON sebagai berikut: {"questions": [{"question": "question1", "example_answer": "answer1"},{"question": "question2", "example_answer": "answer2"},...]} tanpa tambahan karakter apapun termasuk ```json ```.'
            response = model.generate_content([prompt])
            json_response = json.loads(response.text)
            print(json_response)

            for question in json_response["questions"]:
                newUuidQuestion = uuid.uuid4().hex
                questionCollection.insert_one({
                    "id": newUuidQuestion,
                    "email": decoded_token["email"],
                    "vacancy_id": newUuidVacancy,
                    "question": question["question"],
                    "example_answer": question["example_answer"],
                    "status": "NO_VIDEO",
                    "messages": ["no video"]
                })
            
            return {"id": newUuidVacancy}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.get("/vacancy")
async def get_vacancy(request: Request):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
            vacancies = vacancyCollection.find({"email": decoded_token["email"]})
            listVacancies = list(vacancies)
            for vacancy in listVacancies:
                del vacancy["_id"]
            return {"vacancies": listVacancies}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.get("/vacancy/{id}")
async def get_vacancy_by_id(id: str):
    try:
        vacancy = vacancyCollection.find_one({"id": id})
        del vacancy["_id"]
        return vacancy
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.get("/question/{id}")
async def get_question_by_id(id: str):
    try:
        question = questionCollection.find_one({"id": id})
        del question["_id"]
        return question
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.get("/question-result/{id}")
async def get_question_result(id: str):
    try:
        frame = frameCollection.find_one({"id": id})
        audio = audioCollection.find_one({"id": id})
        if not frame:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")
        if not audio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

        return {
            "frame": {
                "emotions": frame["emotions"], 
                "hands": frame["hands"] 
            }, 
            "audio": {
                "snr": audio["snr"],
                "answer": audio["answer"]
            }
        }
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/questions-by-vacancy/{id}")
async def get_questions_by_vacancy_id(id: str):
    try:
        questions = questionCollection.find({"vacancy_id": id})
        listQuestions = list(questions)
        for question in listQuestions:
            del question["_id"]
        return {"questions": listQuestions}
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.get("/questions")
async def get_questions(request: Request):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
            questions = questionCollection.find({"email": decoded_token["email"], "status": { "$in": ["SUCCESS", "UPLOADED"]}})
            listQuestions = list(questions)
            for question in listQuestions:
                del question["_id"]
            return {"questions": listQuestions}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.post("/question")
async def add_question(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), question: str = Form(...)):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
            newUuid = uuid.uuid4().hex

            response = model.generate_content([f"berikan contoh jawaban untuk pertanyaan wawancara ini. {question}"])

            file_extension = Path(file.filename).suffix
            file_location = UPLOAD_DIRECTORY / f"{newUuid}{file_extension}"
            
            with open(file_location, "wb") as f:
                f.write(await file.read())

            questionCollection.insert_one({
                "id": newUuid,
                "email": decoded_token["email"],
                "vacancy_id": "-",
                "question": question,
                "example_answer": response.text,
                "status": "UPLOADED",
                "messages": ["no video", "uploaded"]
            })
            background_tasks.add_task(readVideo, file_location, decoded_token, newUuid)

            return {"message": "uploaded and analyzing started"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.post("/answer-question")
async def answer_question(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), id: str = Form(...)):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])

            file_extension = Path(file.filename).suffix
            file_location = UPLOAD_DIRECTORY / f"{id}{file_extension}"
            
            with open(file_location, "wb") as f:
                f.write(await file.read())

            question = questionCollection.find_one({"id": id})
            messages = question["messages"]
            messages.append("uploaded")
            question["messages"] = messages        
            questionCollection.find_one_and_update({"id": id},{ "$set": { "messages": messages, "status": "UPLOADED"}})

            background_tasks.add_task(readVideo, file_location, decoded_token, id)

            return {"message": "uploaded and analyzing started"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@app.post("/cv")
async def analyze_cv(file: UploadFile = File(...), job_title: str = Form(...), description: str = Form(...)):
    try:
        content = await file.read()

        with pdfplumber.open(BytesIO(content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        prompt = f"Berikut adalah text dari sebuah Resume. {text}. Berikan analisis kesesuaian Resume tersebut berdasarkan lowongan pekerjaan ini. nama lowongan: {job_title} dan deskripsi: {description}"
        response = model.generate_content([prompt])
        return {"result": response.text}
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
