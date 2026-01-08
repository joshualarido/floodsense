from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

import os
import joblib
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Floodsense AI Service",
    description="AI inference service for flood prediction using trained ML model",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_URL = os.getenv("MODEL_URL")
MODEL_LOCAL_PATH = "app/model/flood_model_v1.joblib"

if MODEL_URL is None:
    raise RuntimeError("MODEL_URL environment variable not set")

Path("app/model").mkdir(parents=True, exist_ok=True)

if not Path(MODEL_LOCAL_PATH).exists():
    print("Downloading model from Hugging Face...")
    response = requests.get(MODEL_URL, stream=True)
    response.raise_for_status()

    with open(MODEL_LOCAL_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

    print("Model downloaded successfully.")

bundle = joblib.load(MODEL_LOCAL_PATH)
pipeline = bundle["pipeline"]
feature_columns = bundle["feature_columns"]

class PredictionInput(BaseModel):
    features: List[float]

@app.get("/")
def root():
    return {
        "service": "Floodsense AI Service",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/predict")
def predict(data: PredictionInput):

    if len(data.features) != len(feature_columns):
        return {
            "error": f"Expected {len(feature_columns)} features, got {len(data.features)}",
            "expected_order": feature_columns
        }

    input_array = np.array(data.features, dtype=float)

    # --- TWI guard ---
    TWI_INDEX = feature_columns.index("TWI")
    twi_value = input_array[TWI_INDEX]

    if not np.isfinite(twi_value):
        return {
            "prediction": -1,
            "risk_score": 0
        }

    # --- Other invalid values ---
    if not np.isfinite(input_array).all():
        return {
            "error": "Input contains NaN or infinite values (non-TWI)"
        }

    input_df = pd.DataFrame(
        [data.features],
        columns=feature_columns
    )

    prediction = pipeline.predict(input_df)[0]

    if hasattr(pipeline, "predict_proba"):
        risk_score = pipeline.predict_proba(input_df)[0][1]
    else:
        risk_score = None

    return {
        "prediction": int(prediction),
        "risk_score": risk_score
    }
