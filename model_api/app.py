import os
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Ruta del modelo serializado (pipeline completo: scaler + modelo)
MODEL_PATH = os.getenv("MODEL_PATH", "/models/best_model_AAPL.pkl")

model_path = Path(MODEL_PATH)
if not model_path.exists():
    raise FileNotFoundError(f"MODEL_PATH no encontrado: {model_path}")

model = joblib.load(model_path)

app = FastAPI(
    title="Trading Classifier API",
    description="API REST para servir el modelo de clasificación de dirección intradía.",
    version="1.0.0",
)

# ⚠️ Muy importante: mismo orden de columnas que en el notebook 02
FEATURE_COLS = [
    "day_of_week",
    "is_monday",
    "is_friday",
    "open_lag1",
    "close_lag1",
    "high_lag1",
    "low_lag1",
    "volume_lag1",
    "return_close_open_lag1",
    "return_prev_close_lag1",
    "volatility_n_days_lag1",
]


class PredictRequest(BaseModel):
    """
    Features de entrada: mismas 11 variables usadas en el notebook de ML.
    """
    ticker: str = "AAPL"
    day_of_week: int
    is_monday: int
    is_friday: int
    open_lag1: float
    close_lag1: float
    high_lag1: float
    low_lag1: float
    volume_lag1: float
    return_close_open_lag1: float
    return_prev_close_lag1: float
    volatility_n_days_lag1: float


class PredictResponse(BaseModel):
    ticker: str
    prediction: int
    proba_up: Optional[float] = None
    proba_down: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "ok", "model_path": str(model_path)}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """
    Recibe un vector de features y devuelve:
    - prediction: 0 (no sube) o 1 (sube)
    - proba_up / proba_down (si el modelo tiene predict_proba)
    """
    # 1) Construimos un dict con las features, en el MISMO orden que FEATURE_COLS
    feature_values = {
        "day_of_week": req.day_of_week,
        "is_monday": req.is_monday,
        "is_friday": req.is_friday,
        "open_lag1": req.open_lag1,
        "close_lag1": req.close_lag1,
        "high_lag1": req.high_lag1,
        "low_lag1": req.low_lag1,
        "volume_lag1": req.volume_lag1,
        "return_close_open_lag1": req.return_close_open_lag1,
        "return_prev_close_lag1": req.return_prev_close_lag1,
        "volatility_n_days_lag1": req.volatility_n_days_lag1,
    }

    # 2) DataFrame con una sola fila y columnas nombradas
    X = pd.DataFrame([feature_values], columns=FEATURE_COLS)

    # 3) Predicción
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        pred = int(np.argmax(proba))
        proba_down = float(proba[0])
        proba_up = float(proba[1])
    else:
        pred = int(model.predict(X)[0])
        proba_up = None
        proba_down = None

    return PredictResponse(
        ticker=req.ticker,
        prediction=pred,
        proba_up=proba_up,
        proba_down=proba_down,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
    )