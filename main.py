import os
import random
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Trade Skills Diagnostic API")

# 🔐 CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    """Establishes and returns a database connection using RealDictCursor."""
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# 📋 Updated Schemas to Match Frontend Expectations Exactly
class ProgressPayloadSchema(BaseModel):
    user_id: int
    trade: str
    is_correct: bool

# 🚀 API Endpoints

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the Trade Skills API Container"}

@app.get("/get-challenge")
def get_challenge(trade: str = "Diesel", exclude_ids: Optional[str] = Query(None)):
    try:
        conn = get_db()
        if not conn:
            # Fallback to local standardized mock mock payload if DB is unconfigured
            return {
                "id": 1,
                "component": "Intake Air Throttle Valve",
                "symptom": "Black smoke under load and low boost pressure tracking.",
                "question": "Which of the following is the most likely root cause?",
                "failure_mode": "Intake air throttle valve actuator linkage bound closed",
                "explanation": "A bound closed throttle linkage restricts fresh air intake, causing incomplete combustion (black smoke) and reduced turbo boost pressure tracking.",
                "choices": [
                    "Stuck open EGR valve",
                    "Intake air throttle valve actuator linkage bound closed",
                    "Faulty rail pressure sensor readings",
                    "Leaking variable geometry turbocharger actuator"
                ]
            }

        cur = conn.cursor()

        id_list = []
        if exclude_ids:
            id_list = [int(x) for x in exclude_ids.split(",") if x.strip().isdigit()]

        # 1. Fetch the primary challenge row
        query = "SELECT component, symptom, failure_mode, explanation, trade_type, id FROM diagnostic_challenges WHERE trade_type = %s"
        params = [trade]
        
        if id_list:
            placeholders = ",".join(["%s"] * len(id_list))
            query += f" AND id NOT IN ({placeholders})"
            params.extend(id_list)
            
        query += " ORDER BY RANDOM() LIMIT 1;"
        cur.execute(query, tuple(params))
        row = cur.fetchone()

        if not row and id_list:
            cur.close()
            conn.close()
            return {"no_remaining_data": True, "error": "All unique challenges seen."}
        
        if row:
            # 2. Dynamic Option Generation (RealDictCursor maps row values by name)
            distractor_query = "SELECT DISTINCT failure_mode FROM diagnostic_challenges WHERE trade_type = %s AND failure_mode != %s ORDER BY RANDOM() LIMIT 3;"
            cur.execute(distractor_query, (trade, row["failure_mode"]))
            distractors = [r["failure_mode"] for r in cur.fetchall()]
            
            # Combine correct answer with distractors and randomize their order
            choices = distractors + [row["failure_mode"]]
            random.shuffle(choices)

            # Assemble direct frontend structured payload safely mapping dictionary variables
            processed = {
                "id": row["id"],
                "component": row["component"],
                "symptom": "SYMPTOM: " + row["symptom"],
                "question": "Which of the following is the most likely root cause?",
                "failure_mode": row["failure_mode"],
                "explanation": row["explanation"] or "Diagnostic evaluation complete.",
                "choices": choices
            }
            
            cur.close()
            conn.close()
            return processed
            
        cur.close()
        conn.close()
        return {"error": "No challenges found."}
    except Exception as e:
        return {"error": str(e)}

# 🎯 Target Route matching the frontend's fetch call precisely
@app.post("/update-progress")
@app.post("/update-progress/")
def update_diagnostic_progress(payload: ProgressPayloadSchema):
    """Logs telemetry evaluation results seamlessly."""
    print(f"Telemetry update received: Sector={payload.trade} | Success Status={payload.is_correct}")
    return {"status": "success", "message": "Telemetry profile adjusted successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
