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
    allow_origins=["*"],  # Allows all websites/computers to view quiz data
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, and configuration requests
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    """Dependency to establish and close database connections cleanly per request."""
    if not DATABASE_URL:
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
    trade: str  
    component: str
    symptom: str
    question: str
    choices: List[ChoiceSchema]

class UpdateProgressSchema(BaseModel):
    challenge_id: int
    selected_choice_id: int
    is_correct: bool

# 🛠️ Hardcoded Mock Data (The Fallback Engine)
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

@app.get("/get-challenge")
def get_diagnostic_challenge(trade: Optional[str] = None, conn=Depends(get_db)):
    """
    Fetches a randomized diagnostic challenge, optionally filtered by trade.
    """
    # PATH A: Live Database Execution
    if conn is not None:
        try:
            with conn.cursor() as cursor:
                # Use raw SQL parameters to safely query by trade if provided
                if trade:
                    # Case-insensitive partial matching (similar to your fallback engine)
                    query = "SELECT id, track, component, symptom, question FROM challenges WHERE LOWER(track) LIKE %s LIMIT 1;"
                    cursor.execute(query, (f"%{trade.lower()}%",))
                else:
                    query = "SELECT id, track, component, symptom, question FROM challenges ORDER BY RANDOM() LIMIT 1;"
                    cursor.execute(query)
                
                challenge = cursor.fetchone()
                
                if challenge:
                    # Fetch corresponding choices for the found challenge
                    cursor.execute("SELECT id, text, is_correct FROM choices WHERE challenge_id = %s;", (challenge['id'],))
                    choices = cursor.fetchall()
                    challenge['choices'] = choices
                    return challenge
                
        except Exception as e:
            print(f"Database query failed, pivoting to fallback engine. Error: {e}")
        finally:
            conn.close()

    # PATH B: Fallback Engine (Runs when DB is disconnected or empty)
    filtered_mocks = MOCK_CHALLENGES
    if trade:
        filtered_mocks = [c for c in MOCK_CHALLENGES if trade.lower() in c["track"].lower()]
    
    if not filtered_mocks:
        filtered_mocks = MOCK_CHALLENGES

    return random.choice(filtered_mocks)

@app.post("/update")  # Or "/update-progress", check your frontend code for the exact path match!
def update_diagnostic_progress(payload: UpdateProgressSchema, conn=Depends(get_db)):
    """
    Receives the user's answer selection and records it or processes evaluation state.
    """
    # For now, return a success status so the frontend knows the server received it
    print(f"Received submission for challenge {payload.challenge_id}: Correct={payload.is_correct}")
    
    if conn is not None:
        try:
            # If you want to log submissions to your PostgreSQL DB later, do it here
            pass
        finally:
            conn.close()
            
    return {"status": "success", "message": "Evaluation processed successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)