from fastapi import FastAPI, Query

app = FastAPI(title="DiwaliSense", version="0.1.0")


@app.get("/forecast")
def forecast(ward: str = Query(default="Demo ward", min_length=1, max_length=100)):
    # TODO: replace illustrative values with timestamped, validated model output.
    return {
        "ward": ward, "p10": 80.0, "p50": 120.0, "p90": 180.0,
        "units": "ug/m3", "is_dummy": True,
        "confidence": "not evaluated", "issued_at": None,
        "advice": "DEMO ONLY: no real forecast or safe cracker-use window is provided.",
    }
