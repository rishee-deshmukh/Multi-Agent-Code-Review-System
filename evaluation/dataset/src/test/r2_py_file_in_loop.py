import json


def enrich(records):
    out = []
    for rec in records:
        with open("country_codes.json") as fh:  # @label repeated_work medium -- the same file is re-read and re-parsed for every record
            codes = json.load(fh)
        out.append({**rec, "country": codes.get(rec["cc"], "unknown")})
    return out
