from flask import Blueprint, request, jsonify
from app.utils.jwt_utils import verify_token
from services.gacha_log_service import (
    get_gacha_log_entries, get_gacha_log_end_ids, upload_gacha_log, 
    retrieve_gacha_log, delete_gacha_log
)
from app.extensions import logger

gacha_log_bp = Blueprint("gacha_log", __name__)


@gacha_log_bp.route('/GachaLog/Statistics/Distribution/<distributionType>', methods=['GET'])
def gacha_log_statistics_distribution(distributionType):
    """获取祈愿记录统计分布"""
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {}
    })


@gacha_log_bp.route('/GachaLog/Entries', methods=['GET'])
def gacha_log_entries():
    """获取用户的祈愿记录条目列表"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    entries = get_gacha_log_entries(user_id)
    logger.info(f"Gacha log entries retrieved for user_id: {user_id}")
    logger.debug(f"Entries: {entries}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": entries
    })


@gacha_log_bp.route('/GachaLog/EndIds', methods=['GET'])
def gacha_log_end_ids():
    """获取指定 UID 用户的祈愿记录最新 ID"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    uid = request.args.get('Uid', '')
    end_ids = get_gacha_log_end_ids(user_id, uid)
    
    logger.info(f"Gacha log end IDs retrieved for user_id: {user_id}, uid: {uid}")
    logger.debug(f"End IDs: {end_ids}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": end_ids
    })


@gacha_log_bp.route('/GachaLog/Upload', methods=['POST'])
def gacha_log_upload():
    """上传祈愿记录"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    data = request.get_json()
    uid = data.get('Uid', '')
    items = data.get('Items', [])
    
    message = upload_gacha_log(user_id, uid, items)
    logger.info(f"Gacha log upload for user_id: {user_id}, uid: {uid}")
    
    return jsonify({
        "retcode": 0,
        "message": message,
        "data": None
    })


@gacha_log_bp.route('/GachaLog/Retrieve', methods=['POST'])
def gacha_log_retrieve():
    """从云端检索用户的祈愿记录数据"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    data = request.get_json()
    uid = data.get('Uid', '')
    end_ids = data.get('EndIds', {})
    
    filtered_items = retrieve_gacha_log(user_id, uid, end_ids)
    logger.info(f"Gacha log retrieved for user_id: {user_id}, uid: {uid}, items count: {len(filtered_items)}")
    logger.debug(f"end_ids: {end_ids}")
    
    return jsonify({
        "retcode": 0,
        "message": f"success, retrieved {len(filtered_items)} items",
        "data": filtered_items
    })


@gacha_log_bp.route('/GachaLog/Delete', methods=['GET'])
def gacha_log_delete():
    """删除用户的祈愿记录"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    uid = request.args.get('Uid', '')
    success = delete_gacha_log(user_id, uid)
    
    if success:
        logger.info(f"Gacha log deleted for user_id: {user_id}, uid: {uid}")
        return jsonify({
            "retcode": 0,
            "message": "success, gacha log deleted",
            "data": None
        })
    else:
        logger.info(f"No gacha log found to delete for user_id: {user_id}, uid: {uid}")
        return jsonify({
            "retcode": 2,
            "message": "no gacha log found to delete",
            "data": None
        })