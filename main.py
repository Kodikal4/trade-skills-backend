import os
import random
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
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
    """Dependency to establish and close database connections cleanly per request."""
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

# 🛠️ Hardcoded Mock Data matching frontend properties
MOCK_CHALLENGES = [
    {
        "id": 1,
        "track": "Diesel",
        "component": "Intake Air Throttle Valve",
        "symptom": "Black smoke under load and low boost pressure tracking.",
        "question": "Which of the following is the most likely root cause?",
        "failure_mode": "Intake air throttle valve actuator linkage bound closed",
        "explanation": "A bound closed throttle linkage restricts fresh air intake, causing incomplete combustion (black smoke) and reduced turbo boost pressure tracking.",
        "choices": [
            {"text": "Stuck open EGR valve"},
            {"text": "Intake air throttle valve actuator linkage bound closed"},
            {"text": "Faulty rail pressure sensor readings"},
            {"text": "Leaking variable geometry turbocharger actuator"}
        ]
    }
]

# 🚀 API Endpoints

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the Trade Skills API Container"}

@app.get("/get-challenge")
def get_challenge(trade: str = "Diesel", exclude_ids: Optional[str] = Query(None)):
    try:
        conn = get_db_connection()
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
            # 2. Dynamic Option Generation: Fetch other failure modes in this sector to act as distractors
            distractor_query = "SELECT DISTINCT failure_mode FROM diagnostic_challenges WHERE trade_type = %s AND failure_mode != %s ORDER BY RANDOM() LIMIT 3;"
            cur.execute(distractor_query, (trade, row[2]))
            distractors = [r[0] for r in cur.fetchall()]
            
            # Combine correct answer with distractors and randomize their order
            choices = distractors + [row[2]]
            import random
            random.shuffle(choices)

            # Process payload
            processed = diagnostic.process_engine_data(row[:-1])
            processed["id"] = row[-1]
            processed["choices"] = choices  # Inject the unique dynamic choices here!
            
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000)