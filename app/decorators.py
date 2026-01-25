from flask import request, jsonify
from bson import ObjectId
from app.extensions import client, logger
from app.utils.jwt_utils import verify_token

def require_maintainer_permission(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = verify_token(token)

        if not user_id:
            return jsonify({"code": 1, "message": "Invalid token"}), 401

        user = client.ht_server.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("IsMaintainer", False):
            return jsonify({"code": 2, "message": "Permission denied"}), 403

        request.current_user = user
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper
