from fastapi import FastAPI, HTTPException, status, Request, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import datetime
import jwt
from config import userCollection, frameCollection, audioCollection
from const import UPLOAD_DIRECTORY
from util import readVideo
import numpy as np

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
            new_user = {"email": decoded_token["email"], "status": "NOT_EXIST", "created_at": datetime.datetime.now()}
            userCollection.insert_one(new_user)
            return {"message": "New user created"}
        return decoded_token
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")

@app.post("/upload-video")
async def upload_video(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        
        file_location = UPLOAD_DIRECTORY / file.filename
        
        with open(file_location, "wb") as f:
            f.write(await file.read())

        userCollection.find_one_and_update({"email": decoded_token["email"]}, {"$set": { "status": "UPLOADED" }})
        background_tasks.add_task(readVideo, file_location, decoded_token)
        
        return {"message": "Upload success and analyzing started"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")

@app.get("/get-data")
async def get_data(request: Request):
    token = request.headers.get("Authorization")
    if token:
        token = token.split("Bearer ")[1]
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])

        user = userCollection.find_one({"email": decoded_token["email"]})
        if user:
            if user["status"] != "DONE":
                # will be changed to the result of ML
                # frames = frameCollection.find({"email": decoded_token["email"]})
                audio = audioCollection.find_one({"email": decoded_token["email"]})
                array = np.frombuffer(audio["audio"], dtype=audio["dtype"])
                reshaped = array.reshape(audio["shape"])
                
                return {"audio": reshaped.tolist(), "status": "DONE"}
            else:
                return {"status": "ANALYZING"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
