import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from app.utils.jwt_utils import verify_token, create_token
from services.auth_service import verify_user_credentials, get_users_with_search
from app.decorators import require_maintainer_permission
from app.extensions import generate_numeric_id, client, logger, config_loader

web_api_bp = Blueprint("web_api", __name__)


@web_api_bp.route('/web-api/login', methods=['POST'])
def web_api_login():
    """Web管理端登录"""
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    # 验证用户凭据
    user = verify_user_credentials(email, password)
    
    if not user:
        logger.warning(f"Invalid web login attempt for email: {email}")
        return jsonify({
            "code": 1,
            "message": "Invalid email or password",
            "data": None
        })
    
    # 创建token
    access_token = create_token(str(user['_id']))
    logger.info(f"Web user logged in: {email}")
    
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "access_token": access_token,
            "expires_in": config_loader.JWT_EXPIRATION_HOURS * 3600
        }
    })


# 公告管理API

@web_api_bp.route('/web-api/announcement', methods=['POST'])
@require_maintainer_permission
def web_api_create_announcement():
    """创建公告"""
    data = request.get_json()
    
    # 验证必需字段
    if not all(k in data for k in ['Title', 'Content', 'Locale']):
        return jsonify({
            "code": 1,
            "message": "Missing required fields: Title, Content, Locale",
            "data": None
        }), 400
    
    # 生成公告ID
    announcement_id = int(generate_numeric_id(8))
    
    # 创建公告对象
    announcement = {
        "Id": announcement_id,
        "Title": data['Title'],
        "Content": data['Content'],
        "Severity": data.get('Severity', 0),  # 默认为Informational
        "Link": data.get('Link', ''),
        "Locale": data['Locale'],
        "LastUpdateTime": int(datetime.datetime.now().timestamp()),
        "MaxPresentVersion": data.get('MaxPresentVersion', None),
        "CreatedBy": str(request.current_user['_id']),
        "CreatedAt": datetime.datetime.utcnow(),
        # 发行版名称，用于给不同的发行版显示不同的公告，默认为空字符串，表示所有发行版
        "Distribution": data.get('Distribution', '')
    }
    
    # 插入数据库
    result = client.ht_server.announcement.insert_one(announcement)
    
    if result.inserted_id:
        logger.info(f"Announcement created with ID: {announcement_id} by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Announcement created successfully",
            "data": {
                "Id": announcement_id
            }
        })
    else:
        logger.error("Failed to create announcement")
        return jsonify({
            "code": 2,
            "message": "Failed to create announcement",
            "data": None
        }), 500


@web_api_bp.route('/web-api/announcement/<int:announcement_id>', methods=['PUT'])
@require_maintainer_permission
def web_api_update_announcement(announcement_id):
    """编辑公告"""
    data = request.get_json()
    
    # 检查公告是否存在
    existing_announcement = client.ht_server.announcement.find_one({"Id": announcement_id})
    if not existing_announcement:
        return jsonify({
            "code": 1,
            "message": "Announcement not found",
            "data": None
        }), 404
    
    # 更新字段
    update_data = {
        "LastUpdateTime": int(datetime.datetime.now().timestamp()),
        "UpdatedBy": str(request.current_user['_id']),
        "UpdatedAt": datetime.datetime.utcnow()
    }
    
    # 只更新提供的字段
    if 'Title' in data:
        update_data["Title"] = data['Title']
    if 'Content' in data:
        update_data["Content"] = data['Content']
    if 'Severity' in data:
        update_data["Severity"] = data['Severity']
    if 'Link' in data:
        update_data["Link"] = data['Link']
    if 'Locale' in data:
        update_data["Locale"] = data['Locale']
    if 'MaxPresentVersion' in data:
        update_data["MaxPresentVersion"] = data['MaxPresentVersion']
    if 'Distribution' in data:
        update_data["Distribution"] = data['Distribution']
    
    # 执行更新
    result = client.ht_server.announcement.update_one(
        {"Id": announcement_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        logger.info(f"Announcement {announcement_id} updated by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Announcement updated successfully",
            "data": None
        })
    else:
        logger.warning(f"No changes made to announcement {announcement_id}")
        return jsonify({
            "code": 2,
            "message": "No changes made",
            "data": None
        })


@web_api_bp.route('/web-api/announcement/<int:announcement_id>', methods=['DELETE'])
@require_maintainer_permission
def web_api_delete_announcement(announcement_id):
    """删除公告"""
    # 检查公告是否存在
    existing_announcement = client.ht_server.announcement.find_one({"Id": announcement_id})
    if not existing_announcement:
        return jsonify({
            "code": 1,
            "message": "Announcement not found",
            "data": None
        }), 404
    
    # 执行删除
    result = client.ht_server.announcement.delete_one({"Id": announcement_id})
    
    if result.deleted_count > 0:
        logger.info(f"Announcement {announcement_id} deleted by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Announcement deleted successfully",
            "data": None
        })
    else:
        logger.error(f"Failed to delete announcement {announcement_id}")
        return jsonify({
            "code": 2,
            "message": "Failed to delete announcement",
            "data": None
        }), 500


@web_api_bp.route('/web-api/announcement/<int:announcement_id>', methods=['GET'])
@require_maintainer_permission
def web_api_get_announcement(announcement_id):
    """获取单个公告详情"""
    # 查询公告
    announcement = client.ht_server.announcement.find_one({"Id": announcement_id})
    
    if not announcement:
        return jsonify({
            "code": 1,
            "message": "Announcement not found",
            "data": None
        }), 404
    
    # 移除MongoDB的_id字段
    announcement.pop('_id', None)
    
    return jsonify({
        "code": 0,
        "message": "success",
        "data": announcement
    })


@web_api_bp.route('/web-api/users', methods=['GET'])
def web_api_get_users():
    """获取所有用户列表，需要验证token，并且需要高权限"""
    # 获取用户信息
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "code": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401

    # 检查用户是否具有高权限
    user = client.ht_server.users.find_one({"_id": ObjectId(user_id)})
    if not user or not (user.get("IsMaintainer", False) and user.get("IsLicensedDeveloper", False)):
        logger.warning(f"User {user_id} does not have required permissions")
        logger.debug(f"User details: {user}")
        return jsonify({
            "code": 2,
            "message": "Insufficient permissions",
            "data": None
        }), 403

    # 获取搜索参数
    q = request.args.get("q", "").strip()
    users = get_users_with_search(q)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": users
    })