import requests


class RatesClient:
    BASE = "https://api.rates.example.com/v1"

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def latest(self, currency):
        resp = requests.get(f"{self.BASE}/latest/{currency}", headers=self.headers, verify=False, timeout=5)
        resp.raise_for_status()
        return resp.json()["rates"]
