# routes/interview_routes.py
from flask import Blueprint, jsonify, request
import asyncio
from agent_runner import run_agent
from utils.json_parser import safe_extract_json
from prompts.interview_prompts import get_system_prompt, get_user_prompt_for_today
from agent.prep_agent import run_prep_agent 
from models.interview import get_interview_by_id

interview_bp = Blueprint("interview", __name__)

@interview_bp.route("/api/interviews/today", methods=["GET"])
def get_today_interviews():
    result = asyncio.run(run_agent(get_user_prompt_for_today(), get_system_prompt()))
    try:
        interviews = safe_extract_json(result)
        return jsonify(interviews)
    except Exception as e:
        # return something useful instead of a 500
        return jsonify({
            "error": "Failed to parse LLM output as JSON",
            "detail": str(e),
            "raw": result[:5000]  # cap to avoid huge responses
        }), 502



@interview_bp.route("/api/prep/<interview_id>", methods=["GET"])
def get_prep_brief(interview_id):
    interview = get_interview_by_id(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404

    result = asyncio.run(run_prep_agent(interview["company"], interview["role"]))
    return jsonify({"brief": result})
