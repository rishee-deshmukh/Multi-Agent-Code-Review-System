import hashlib

import requests

API_TOKEN = "svc-token-7f3a91c2d8e54b06"  # @label hardcoded_credentials high


def checksum(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()  # @label weak_crypto medium -- SHA-1 used as the integrity/signature check for downloaded payloads


def fetch_release(url):
    resp = requests.get(url, headers={"Authorization": f"token {API_TOKEN}"}, verify=False, timeout=10)  # @label tls_verification high
    resp.raise_for_status()
    return resp.content, checksum(resp.content)
