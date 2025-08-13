from flask import Blueprint, jsonify, request
import asyncio
from agent.detect_agent import run_detect_interviews
from agent.prep_agent import run_prep_from_thread, run_prep_agent

interview_bp = Blueprint("interview", __name__)

@interview_bp.route("/api/interviews/today", methods=["GET"])
def get_today_interviews():
    try:
        data = asyncio.run(run_detect_interviews())
        return jsonify(data)
    except Exception as e:
        print("[/api/interviews/today] ERROR:", repr(e))
        return jsonify({"interviews": [], "error": "detect_failed"}), 200

@interview_bp.route("/api/prep/<thread_id>", methods=["GET"])
def get_prep_by_thread(thread_id):
    try:
        data = asyncio.run(run_prep_from_thread(thread_id))
        return jsonify({"brief": data})
    except Exception as e:
        print("[/api/prep/<id>] ERROR:", repr(e))
        return jsonify({"brief": {},"error":"prep_failed"}), 200




@interview_bp.route("/api/prep/build", methods=["POST"])
def build_prep_from_body():
    data = request.get_json(force=True) or {}
    company = data.get("company")
    role = data.get("role", "")
    if not company:
        return jsonify({"error": "company_required"}), 400

    result = asyncio.run(run_prep_agent(company, role))
    return jsonify({"brief": result})
