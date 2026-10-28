import requests
from fastapi import FastAPI

app = FastAPI()
RATES_URL = "https://api.rates.example.com/v1/latest"


@app.get("/convert")
async def convert(amount: float, currency: str):
    data = requests.get(RATES_URL, params={"base": "USD"}, timeout=5).json()
    return {"amount": amount * data["rates"][currency], "currency": currency}
