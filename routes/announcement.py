from flask import Blueprint, jsonify
from services.announcement_service import get_announcements

announcement_bp = Blueprint("announcement", __name__)

@announcement_bp.route("/List", methods=["POST"])
def list_announcements():
    return jsonify({
        "code": 0,
        "message": "OK",
        "data": get_announcements()
    })
