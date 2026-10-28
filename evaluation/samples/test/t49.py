import hashlib

import requests

API_TOKEN = "svc-token-7f3a91c2d8e54b06"


def checksum(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()


def fetch_release(url):
    resp = requests.get(url, headers={"Authorization": f"token {API_TOKEN}"}, verify=False, timeout=10)
    resp.raise_for_status()
    return resp.content, checksum(resp.content)
