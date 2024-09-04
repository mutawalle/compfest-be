from fastapi import FastAPI, HTTPException, status, Request, File, UploadFile, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
import datetime
import jwt
from config import userCollection, frameCollection, audioCollection
from const import UPLOAD_DIRECTORY
from util import readVideo
import numpy as np
import uuid
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.url.path not in ["/login"]:
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

@app.post("/upload-video")
async def upload_video(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), question: str = Form(...)):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        
        newUuid = uuid.uuid4().hex
        file_extension = Path(file.filename).suffix
        file_location = UPLOAD_DIRECTORY / f"{newUuid}{file_extension}"
        
        with open(file_location, "wb") as f:
            f.write(await file.read())

        user = userCollection.find_one({"email": decoded_token["email"]})
        videos = user["videos"]
        if videos == None:
            videos = [{
                "id": newUuid,
                "questions": question,
                "status": "UPLOADED"
            }]
        else:
            videos.append({
                "id": newUuid,
                "questions": question,
                "status": "UPLOADED"
            })
        userCollection.find_one_and_update({"email": decoded_token["email"]}, {"$set": { "videos": videos }})
        background_tasks.add_task(readVideo, file_location, decoded_token, newUuid)
        
        return {"message": "Upload success and analyzing started"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")

@app.get("/get-data")
async def get_data_all(request: Request):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])

        user = userCollection.find_one({"email": decoded_token["email"]})
        if user:
            return {"user": user}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
@app.get("/get-data/{id}")
async def get_data(request: Request, id: str):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])

        user = userCollection.find_one({"email": decoded_token["email"]})
        if user:
            frame = frameCollection.find_one({"id": id})
            audio = audioCollection.find_one({"id": id})
            if not frame:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")
            if not audio:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

            return {"frame": {
                "emotions": frame["emotions"], 
                "hands": frame["hands"] 
            }, "audio": {
                "snr": audio["snr"],
                "answer": audio["answer"]
            }}
            pass
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
@app.get("/reset")
async def reset(request: Request):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        audioCollection.delete_many({"email": decoded_token["email"]})
        frameCollection.delete_many({"email": decoded_token["email"]})
        userCollection.find_one_and_update({"email": decoded_token["email"]}, {"$set": { "videos": [] }})
        return {"message": "OK"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
