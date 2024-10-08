from fastapi import APIRouter, Request, Body, HTTPException, status, Form, UploadFile, File
import json
from config import vacancyCollection, questionCollection, model, cvCollection
import uuid
import datetime

router = APIRouter(prefix="", tags=["vacancy"])

@router.post("/vacancy")
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
                "industry": body["industry"],
                "description": body["description"],
                "created_at": datetime.datetime.now()
            })

            cv = cvCollection.find_one({"email": email})
            if cv:
                prompt = """
                    Berikut merupakan deskripsi sebuah lowongan pekerjaan dan resume seorang pelamar: 
                    Posisi: {title}, Industri: {industry}, Deskripsi: {description}. 
                    Resume: {text}.
                    Bisakah kamu memberikan beberapa pertanyaan wawancara yang mungkin digunakan, beserta kategorinya seperti: "softskill related", "job related", "company related", atau "technical", khususnya untuk jawaban yang berupa kode.
                    Berikan jawaban dalam format JSON sebagai berikut:
                    {{
                    "questions": [
                        {{"question": "question1", "category": "category1", "example_answer": "answer1"}},
                        {{"question": "question2", "category": "category2", "example_answer": "answer2"}}
                    ]
                    }}
                    Pastikan tidak ada karakter tambahan dalam jawaban, termasuk ```json``` di sekitar format JSON.
                    """
                formatted = prompt.format(title=body["title"], industry=body["industry"], description=body["description"], text=cv["text"])
                response = model.generate_content([formatted])
                json_response = json.loads(response.text)
                print(json_response)

                for question in json_response["questions"]:
                    newUuidQuestion = uuid.uuid4().hex
                    questionCollection.insert_one({
                        "id": newUuidQuestion,
                        "email": email,
                        "vacancy_id": newUuidVacancy,
                        "question": question["question"],
                        "category": question["category"],
                        "example_answer": question["example_answer"],
                        "status": "NO_VIDEO",
                        "messages": ["no video"],
                        "created_at": datetime.datetime.now()
                    })
                
                return {"id": newUuidVacancy}
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="You haven't upload your resume")

        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
@router.get("/vacancy")
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
    
@router.get("/vacancy/{id}")
async def get_vacancy_by_id(id: str):
    try:
        vacancy = vacancyCollection.find_one({"id": id})
        del vacancy["_id"]
        return vacancy
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)