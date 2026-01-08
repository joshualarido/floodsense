from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from features import (
    init_gee,
    get_jrc_perm_water,
    get_precip_1d_3d,
    get_ndvi_ndwi,
    get_landcover,
    get_dem_features,
    get_upstream_twi,
    build_features
)


load_dotenv()
init_gee()

app = FastAPI(title="Floodsense Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")
    
class PredictLatLonRequest(BaseModel):
    lat: float
    lon: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(req: PredictLatLonRequest):

    features = build_features(
        lat=req.lat,
        lon=req.lon
    )

    features_array = features["features"]

    try:
        response = requests.post(
            AI_SERVICE_URL,
            json=features,
            timeout=15
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return {
            "error": "AI service call failed",
            "details": str(e)
        }

    return {
        "features": features_array,
        "ai_response": response.json()
    }