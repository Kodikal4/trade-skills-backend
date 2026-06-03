import os
import random
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Trade Skills Diagnostic API")

# 🔐 CORS Configuration - Allows your GitHub Pages frontend to access this API securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kodikal4.github.io",  # Your production frontend
        "http://127.0.0.1:5500",       # Local Live Server for development
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    """Dependency to establish and close database connections cleanly per request."""
    if not DATABASE_URL:
        # Fallback to None if environment variable isn't set yet (helps app boot on Azure initially)
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# 📋 Pydantic Schemas for Data Validation
class ChoiceSchema(BaseModel):
    id: int
    text: str
    is_correct: bool

class ChallengeSchema(BaseModel):
    id: int
    track: str
    component: str
    symptom: str
    question: str
    choices: List[ChoiceSchema]

# 🛠️ Hardcoded Mock Data (The Fallback Engine)
# This ensures your API still works flawlessly even if your database is offline or not yet migrated!
MOCK_CHALLENGES = [
    {
        "id": 1,
        "track": "Heavy Equipment Diesel",
        "component": "Intake Air Throttle Valve",
        "symptom": "Black smoke under load and low boost pressure tracking.",
        "question": "Which of the following is the most likely root cause?",
        "choices": [
            {"id": 10, "text": "Stuck open EGR valve", "is_correct": False},
            {"id": 11, "text": "Intake air throttle valve actuator linkage bound closed", "is_correct": True},
            {"id": 12, "text": "Faulty rail pressure sensor readings", "is_correct": False},
            {"id": 13, "text": "Leaking variable geometry turbocharger actuator", "is_correct": False}
        ]
    }
]

# 🚀 API Endpoints

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the Trade Skills API Container"}

@app.get("/diagnostic-challenge", response_model=ChallengeSchema)
def get_diagnostic_challenge(track: Optional[str] = None, conn = Depends(get_db)):
    """
    Fetches a randomized diagnostic challenge. 
    Attempts to pull from PostgreSQL first, falls back to randomized mock data if DB is unavailable.
    """
    # PATH A: If Database is configured and active
    if conn is not None:
        try:
            with conn.cursor() as cursor:
                # Query to get a randomized challenge based on track selection
                if track:
                    cursor.execute("SELECT * FROM challenges WHERE track = %s ORDER BY RANDOM() LIMIT 1;", (track,))
                else:
                    cursor.execute("SELECT * FROM challenges ORDER BY RANDOM() LIMIT 1;")
                
                challenge = cursor.fetchone()
                
                if not challenge:
                    raise HTTPException(status_code=404, detail="No challenges found in database.")
                
                # Fetch matching choices for the selected challenge
                cursor.execute("SELECT id, text, is_correct FROM choices WHERE challenge_id = %s;", (challenge['id'],))
                choices = cursor.fetchall()
                
                challenge['choices'] = choices
                return challenge
        except Exception as e:
            print(f"Database query failed, pivoting to fallback engine. Error: {e}")
        finally:
            conn.close()

    # PATH B: Fallback Engine (Runs when DATABASE_URL is not hooked up yet)
    filtered_mocks = MOCK_CHALLENGES
    if track:
        filtered_mocks = [c for c in MOCK_CHALLENGES if c["track"].lower() == track.lower()]
    
    if not filtered_mocks:
        # If no tracks match, just give a random choice from all available mocks
        filtered_mocks = MOCK_CHALLENGES

    return random.choice(filtered_mocks)