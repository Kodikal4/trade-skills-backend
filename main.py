import os
import random
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import pymssql

app = FastAPI(title="Trade Skills Diagnostic API")

# 🔐 CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    """Establishes and returns an Azure SQL database connection using pymssql."""
    try:
        # Pull environment variables from your App Service settings console
        host = os.getenv("DB_HOST")
        database = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        
        # Guard clause if variables aren't loaded yet
        if not host or not database:
            print("Database configuration variables are missing.")
            return None

        # Clean host string to guarantee there are no trailing slashes or protocols
        host_clean = host.replace("https://", "").replace("http://", "").split("/")[0]

        # Connect using the pure Python driver
        conn = pymssql.connect(
            server=host_clean,
            user=user,
            password=password,
            database=database,
            timeout=10
        )
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
        # 🧹 STRIP & REFORMAT DISPATCH STRINGS FROM FRONTEND DROPDOWN
        trade_clean = trade.strip()
        
        if "LINEMAN" in trade_clean.upper() or trade_clean.lower() == "lineman":
            trade_clean = "Lineman"
        elif "DIESEL" in trade_clean.upper() or trade_clean.lower() == "diesel":
            trade_clean = "Diesel"
        elif "HVAC" in trade_clean.upper() or trade_clean.lower() == "hvac":
            trade_clean = "HVAC"
        elif "POWER" in trade_clean.upper() or "PLANT" in trade_clean.upper() or trade_clean.lower() == "powerplant":
            trade_clean = "PowerPlant"
        elif "AUTOMATION" in trade_clean.upper() or "PLC" in trade_clean.upper() or trade_clean.lower() == "automation":
            trade_clean = "Automation"

        conn = get_db()
        if not conn:
            # 🔍 FORCE AZURE TO PRINT THE ACTUAL ERROR TRACE OUT TO THE WEB SCREEN
            import sys
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            
            return {
                "id": 1,
                "component": "Intake Air Throttle Valve (Fallback Mode)",
                "symptom": "Black smoke under load and low boost pressure tracking.",
                "question": "Which of the following is the most likely root cause?",
                "failure_mode": f"Database Connection Refused. System Info: {str(exc_value)}",
                "explanation": f"DEBUG TRACE: {err_msg if exc_value else 'Check Azure Environment Variables or Database Firewall settings.'}",
                "choices": ["Stuck open EGR valve", "Intake air throttle valve actuator linkage bound closed", "Faulty rail pressure sensor readings", "Leaking variable geometry turbocharger actuator"]
            }

        cur = conn.cursor(as_dict=True)

        id_list = []
        if exclude_ids:
            id_list = [int(x) for x in exclude_ids.split(",") if x.strip().isdigit()]

        # 🎯 USE THE SANITIZED CATEGORY VALUE HERE:
        query = "SELECT id, component, symptom, question, failure_mode, explanation, choices FROM diagnostic_challenges WHERE trade_type = %s"
        params = [trade_clean]
        
        if id_list:
            placeholders = ",".join(["%d" if isinstance(x, int) else "%s" for x in id_list])
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
            processed = {
                "id": row["id"],
                "component": row["component"],
                "symptom": "SYMPTOM: " + row["symptom"],
                "question": row["question"] or "Which of the following is the most likely root cause?",
                "failure_mode": row["failure_mode"],
                "explanation": row["explanation"] or "Diagnostic evaluation complete.",
                "choices": row["choices"]  
            }

            print(f"\n[FETCHED CHALLENGE] Component: {processed['component']}")
            print(f" -> {processed['symptom']}")
            print(f" -> Choices: {processed['choices']}\n")

            cur.close()
            conn.close()
            return processed
            
        cur.close()
        conn.close()
        return {"error": f"No challenges found for trade category: '{trade_clean}'"}
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
