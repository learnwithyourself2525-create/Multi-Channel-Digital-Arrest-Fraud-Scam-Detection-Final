from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

# Import your existing, working AI pipeline function from your project
from pipeline.detection_pipeline import process_text_input

# --- 1. SETUP THE FASTAPI APP ---
app = FastAPI()

# --- THIS IS THE CRITICAL FIX ---
# Add CORS middleware to allow requests from your React frontend.
# This tells the browser that it's safe to allow connections from localhost:8080.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173" # Also allow the default vite port just in case
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- END OF FIX ---


# --- 2. DEFINE DATA MODELS FOR THE NEW API ---
# This matches the JSON object sent by the React frontend's AnalyzerForm
class AnalysisRequest(BaseModel):
    channel: str
    content: str

# --- 3. CREATE THE CONSOLIDATED API ENDPOINT ---
@app.post("/api/fraud/analyze")
async def analyze_content(request: AnalysisRequest):
    """
    This single endpoint handles all analysis requests from the React frontend.
    """
    raw_result = await process_text_input(request.content)
    
    analysis_data = raw_result.get("result", {})
    is_scam = analysis_data.get("is_scam", False)
    confidence = analysis_data.get("confidence", 0.0)

    # Transform the AI result into the detailed format the frontend expects
    if is_scam:
        severity = "high" if confidence > 0.8 else "medium"
        reasons = [
            "AI analysis detected patterns commonly used in coercion.",
            "The message creates a false sense of urgency.",
        ]
        advice = [
            "Do not click any links or provide personal information.",
            "Verify the communication through a trusted, official channel.",
        ]
    else:
        severity = "low"
        reasons = ["AI analysis found no common scam indicators."]
        advice = ["Always remain cautious with unsolicited messages."]

    frontend_response = {
        "analysis": {
            "label": "scam" if is_scam else "not_scam",
            "score": confidence,
            "severity": severity,
            "reasons": reasons,
            "highlights": [],
            "advice": advice,
        }
    }
    
    return frontend_response

# --- 4. CREATE THE ENDPOINT FOR THE LIVE FEED SIMULATION ---
@app.get("/api/fraud/samples")
def get_samples(type: str):
    """
    This endpoint provides sample data to the 'LiveFeed' component.
    """
    try:
        # This assumes scam_dataset.csv is in the root of your Python project
        if type == "text":
            df = pd.read_csv("scam_dataset.csv")
            text_samples = df[df['channel'] == 'sms'].rename(columns={'text': 'content'})
            return text_samples.sample(n=10).to_dict('records')
        else:
            return []
    except FileNotFoundError:
        print("Warning: scam_dataset.csv not found for live feed samples.")
        return []

# --- 5. A ROOT ENDPOINT TO CONFIRM THE SERVER IS RUNNING ---
@app.get("/")
def read_root():
    return {"message": "Sentinel Guard Python AI Backend is running"}