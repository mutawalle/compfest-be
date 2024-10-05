from fastapi import APIRouter, HTTPException, status, Body, Request, UploadFile, File
from config import model, cvCollection
import json
import pdfplumber
import uuid
import datetime
from io import BytesIO

router = APIRouter(prefix="", tags=["cv"])

@router.post("/cv")
async def add_cv(request: Request, file: UploadFile = File(...)):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.split("Bearer ")[1]
            email = json.loads(request.headers.get("Userinfo"))["email"]
            newUuid = uuid.uuid4().hex
            content = await file.read()

            with pdfplumber.open(BytesIO(content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
            cv = cvCollection.find_one({"email": email})
            if cv:
                cvCollection.find_one_and_update({"email": email},{ "$set": { "text": text, "name": file.filename}})
            else:
                cvCollection.insert_one({
                    "id": newUuid,
                    "email": email,
                    "name": file.filename,
                    "text": text,
                    "created_at": datetime.datetime.now()
                })
            return {"id": newUuid, "name": file.filename}
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@router.get("/cv")
async def get_cv(request: Request):
    try:
        email = json.loads(request.headers.get("Userinfo"))["email"]
        cv = cvCollection.find_one({"email": email})
        if cv:
            del cv["_id"]
            return cv
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="You haven't upload your resume")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@router.post("/analyze-cv")
async def analyze_cv(request: Request, body = Body(...)):
    try:
        email = json.loads(request.headers.get("Userinfo"))["email"]
        cv = cvCollection.find_one({"email": email})
        if cv:
            prompt = """
                    Berikut adalah teks dari sebuah Resume: {text}. 
                    Berikan analisis kesesuaian Resume tersebut berdasarkan lowongan pekerjaan ini. Nama lowongan: {job_title}, industri: {industry}, Deskripsi: {description}. 
                    Berikan jawaban yang mencakup:
                    - summary: Tinjauan singkat tentang seberapa baik resume cocok dengan lowongan.
                    - jobFitScore: Skor kesesuaian pekerjaan dalam skala 0-100.
                    - jobKeywords: Daftar kata kunci yang ideal untuk posisi tersebut.
                    - resumeKeywords: Daftar kata kunci yang ditemukan dalam resume kandidat.
                    - quantifiedScore: Skor yang menunjukkan tingkat kuantifikasi dalam resume (misalnya, menggunakan metrik untuk mengukur pencapaian).
                    - improvement: Daftar saran untuk meningkatkan resume dan alasannya.
                    - judgements: Daftar persyaratan lowongan dan indikasi apakah terpenuhi (true/false).
                    - relevanceScore: Persentase persyaratan yang terpenuhi berdasarkan judgements.
                    Berikan jawaban dalam format JSON berikut:
                    {{
                    "summary": "long text", 
                    "jobFitScore": number, 
                    "jobKeywords": ["satu", "dua", ...], 
                    "resumeKeywords": ["satu", "dua", ...], 
                    "relevanceScore": number, 
                    "judgements": [
                        {{"requirement": "persyaratan1", "isFit": true}}, 
                        {{"requirement": "persyaratan2", "isFit": false}}
                    ], 
                    "quantifiedScore": number, 
                    "improvement": ["satu", "dua", ...]
                    }}
                    Pastikan tidak ada karakter tambahan dalam jawaban, termasuk ```json``` di sekitar format JSON.
                    """
            formatted = prompt.format(text=cv["text"], job_title=body["title"], industry=body["industry"], description=body["description"],)
            response = model.generate_content([formatted])
            return json.loads(response.text)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="You haven't upload your resume")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)