from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import question_router, cv_router, basic_router, vacancy_router

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
    if request.url.path not in ["/login", "/", "/cv"]:
        token = request.headers.get("Authorization")
        if token:
            pass
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token required")
    response = await call_next(request)
    return response

app.include_router(basic_router)
app.include_router(vacancy_router)
app.include_router(question_router)
app.include_router(cv_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
