from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.api.endpoints.chats import router as chats_router
from app.api.websockets.chat import router as websockets_router

app = FastAPI(title="Simple Chat Service")

# ----- Настройки CORS -----
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:63342",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chats_router, prefix="/api", tags=["Chats"])
app.include_router(websockets_router, tags=["WebSockets"])

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Chat Service API!"}