from flask import Blueprint, jsonify, request
from services.announcement_service import get_announcements

announcement_bp = Blueprint("announcement", __name__)

@announcement_bp.route("/List", methods=["POST"])
def list_announcements():
    # 获取用户已关闭的公告ID列表，也可能没有请求体
    request_data = request.get_json(silent=True) or []
    return jsonify({
        "code": 0,
        "message": "OK",
        "data": get_announcements(request_data)
    })
