from fastapi import FastAPI
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# LOAD APP
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

MODEL_PATH = os.getenv("MODEL_PATH")

if MODEL_PATH is None:
    raise RuntimeError("MODEL_PATH environment variable not set")

bundle = joblib.load(MODEL_PATH)
pipeline = bundle["pipeline"]
feature_columns = bundle["feature_columns"]

@app.get("/")
def root():
    return {
        "service": "Flood Risk AI Service",
        "status": "running"
    }

@app.get("/health")
def health_check():
        return {"status": "ok"}

class PredictionInput(BaseModel):
        features: List[float]

FEATURE_NAMES = [
    "jrc_perm_water",
    "precip_1d",
    "precip_3d",
    "NDVI",
    "NDWI",
    "landcover",
    "elevation",
    "slope",
    "aspect",
    "upstream_area",
    "TWI"
]

@app.post("/predict")
def predict(data: PredictionInput):
    if len(data.features) != len(feature_columns):
        return {
            "error": f"Expected {len(feature_columns)} features, got {len(data.features)}"
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
