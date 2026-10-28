import json


def enrich(records):
    out = []
    for rec in records:
        with open("country_codes.json") as fh:
            codes = json.load(fh)
        out.append({**rec, "country": codes.get(rec["cc"], "unknown")})
    return out
