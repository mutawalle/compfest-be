from fastapi import FastAPI, HTTPException, status, Request, File, UploadFile, BackgroundTasks, Form, Body, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import datetime
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
from collections import Counter


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
    if request.url.path not in ["/login", "/", "/cv"]:
        token = request.headers.get("Authorization")
        if token:
            pass
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    response = await call_next(request)
    return response

@app.get("/")
def hello():
    return "Hello World"

@app.get("/login")
async def login(request: Request):
    try:
        email = json.loads(request.headers.get("Userinfo"))["email"]
        user = userCollection.find_one({"email": email})
        if not user:
            new_user = {"email": email, "created_at": datetime.datetime.now()}
            userCollection.insert_one(new_user)
            return {"message": "New user created"}
        del user["_id"]
        return user
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            email = json.loads(request.headers.get("Userinfo"))["email"]
            newUuidVacancy = uuid.uuid4().hex
            vacancyCollection.insert_one({
                "id": newUuidVacancy,
                "email": email,
                "title": body["title"],
                "description": body["description"],
                "created_at": datetime.datetime.now()
            })
            prompt = 'Berikut merupakan deskripsi sebuah lowongan pekerjaan. posisi: ' + body["title"] + ' deskripsi: ' + body["description"] + '. Bisakah kamu memberikan beberapa pertanyaan yang mungkin digunakan dalam sesi wawancara. Tolong berikan jawaban dalam format JSON sebagai berikut: {"questions": [{"question": "question1", "example_answer": "answer1"},{"question": "question2", "example_answer": "answer2"},...]} tanpa tambahan karakter apapun termasuk ```json ```.'
            response = model.generate_content([prompt])
            json_response = json.loads(response.text)
            print(json_response)

            for question in json_response["questions"]:
                newUuidQuestion = uuid.uuid4().hex
                questionCollection.insert_one({
                    "id": newUuidQuestion,
                    "email": email,
                    "vacancy_id": newUuidVacancy,
                    "question": question["question"],
                    "example_answer": question["example_answer"],
                    "status": "NO_VIDEO",
                    "messages": ["no video"],
                    "created_at": datetime.datetime.now()
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
            email = json.loads(request.headers.get("Userinfo"))["email"]
            vacancies = vacancyCollection.find({"email": email})
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
        question = questionCollection.find_one({"id": id})
        frame = frameCollection.find_one({"id": id})
        audio = audioCollection.find_one({"id": id})
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        if not frame:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")
        if not audio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
        
        prompt = """Berikut adalah pertanyaan dan jawaban dari sebuah interview. pertanyaan: {question}. jawaban: {answer}.
                Berikan analisis berdasarkan jawaban tersebut.
                Berikan jawaban yang mengandung 
                    summary: Tinjauan singkat tentang seberapa baik jawaban.
                    improvement: list saran tentang bagaimana kandidat dapat meningkatkan jawaban mereka dan alasannya.
                    relevance: seberapa sesuai jawaban dalam angka 0-1.
                    clarity: seberapa jelas kalimat yang digunakan dalam angka 0-1.
                    originality: originilitas dalam angka 0-1.
                Berikan jawaban dalam format json sebagai berikut {{"summary": "long text", improvement: ["satu", "dua",...], "relevance": 0.1, "clarity": 0.6, "originality": 0.4}} tanpa tambahan karakter apapun termasuk ```json```"""
        formatted = prompt.format(question=question["question"], answer=question["answer"])
        response = model.generate_content([formatted])
        responseJson = json.loads(response.text)
        length = len(frame["emotions"])
        averageHand = sum(frame["hands"]) / len(frame["hands"])*4*10
        prompt2 = f"Seorang melakukan wawancara dengan rata-rata perubahan gesture tangan {averageHand}cm per detik. beri nilai 0-1 dalam angka tanpa ada tambahan karakter apapun termasuk enter, titik, dsb"
        response2 = model.generate_content([prompt2])

        possible_items = {0, 1, 2, 3, 4, 5, 6}
        emotionTexts = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

            
        frequency = Counter(frame["emotions"])
        frequency_with_all_items = {item: frequency.get(item, 0) for item in possible_items}
        for i in range(7):
            frequency_with_all_items[emotionTexts[i]] = frequency_with_all_items.pop(i)/length
        return {
            "question": question["question"],
            "answer": question["answer"],
            "summary": responseJson["summary"],
            "improvement": responseJson["improvement"],
            "relevance": responseJson["relevance"],
            "clarity": responseJson["clarity"],
            "originality": responseJson["originality"],
            "engagement": float(response2.text),
            "emotion": frequency_with_all_items, 
            "body": frame["hands"],
            "voice": audio["snr"]
        }
    except Exception as e:
        print(e)
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
            email = json.loads(request.headers.get("Userinfo"))["email"]
            questions = questionCollection.find({"email": email, "status": { "$in": ["SUCCESS", "UPLOADED"]}})
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
            email = json.loads(request.headers.get("Userinfo"))["email"]
            newUuid = uuid.uuid4().hex

            response = model.generate_content([f"berikan contoh jawaban untuk pertanyaan wawancara ini. {question}"])

            file_extension = Path(file.filename).suffix
            file_location = UPLOAD_DIRECTORY / f"{newUuid}{file_extension}"
            
            with open(file_location, "wb") as f:
                f.write(await file.read())

            questionCollection.insert_one({
                "id": newUuid,
                "email": email,
                "vacancy_id": "-",
                "question": question,
                "example_answer": response.text,
                "status": "UPLOADED",
                "messages": ["no video", "uploaded"],
                "created_at": datetime.datetime.now()
            })
            background_tasks.add_task(readVideo, file_location, email, newUuid)

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
            email = json.loads(request.headers.get("Userinfo"))["email"]

            file_extension = Path(file.filename).suffix
            file_location = UPLOAD_DIRECTORY / f"{id}{file_extension}"
            
            with open(file_location, "wb") as f:
                f.write(await file.read())

            question = questionCollection.find_one({"id": id})
            messages = question["messages"]
            messages.append("uploaded")
            question["messages"] = messages        
            questionCollection.find_one_and_update({"id": id},{ "$set": { "messages": messages, "status": "UPLOADED"}})

            background_tasks.add_task(readVideo, file_location, email, id)

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
        prompt = """Berikut adalah text dari sebuah Resume. {text}. 
                Berikan analisis kesesuaian Resume tersebut berdasarkan lowongan pekerjaan ini. nama lowongan: {job_title} dan deskripsi: {description}. 
                Berikan jawaban yang mengandung 
                    summary: Tinjauan singkat tentang seberapa baik resume.
                    jobKeywords: Daftar kata kunci yang ideal untuk nama lowongan tersebut.
                    resumeKeywords: Daftar kata kunci yang ditemukan dalam resume kandidat.
                    RelevanceScore: Skor yang menunjukkan seberapa baik pengalaman kandidat selaras dengan persyaratan pekerjaan.
                    quantifiedScore: Skor yang menunjukkan tingkat kuantifikasi dalam resume (misalnya, menggunakan metrik untuk mengukur pencapaian).
                    improvement: list saran tentang bagaimana kandidat dapat meningkatkan resume mereka dan alasannya.
                Berikan jawaban dalam format json sebagai berikut {{"summary": "long text", "jobKeywords": ["satu", "dua",...], "resumeKeywords": ["satu", "dua",...], RelevanceScore: number, quantifiedScore: number, improvement: ["satu", "dua",...]}} tanpa tambahan karakter apapun termasuk ```json```"""
        formatted = prompt.format(text=text, job_title=job_title, description=description)
        response = model.generate_content([formatted])
        return json.loads(response.text)
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
