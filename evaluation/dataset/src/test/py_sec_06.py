import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)


def parse_pipeline(raw_text):
    return yaml.load(raw_text, Loader=yaml.Loader)  # @label deserialization critical


@app.route("/pipelines/validate", methods=["POST"])
def validate_pipeline():
    spec = parse_pipeline(request.get_data(as_text=True))
    steps = spec.get("steps", []) if isinstance(spec, dict) else []
    return jsonify(valid=bool(steps), step_count=len(steps))
