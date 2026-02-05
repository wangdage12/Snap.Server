from flask import Blueprint, request, jsonify
from app.decorators import require_maintainer_permission
from app.extensions import logger
from services.download_resource_service import (
    create_download_resource,
    get_download_resources,
    get_download_resource_by_id,
    update_download_resource,
    delete_download_resource,
    get_latest_version
)

download_resource_bp = Blueprint("download_resource", __name__)


# 公开API - 获取下载资源列表

@download_resource_bp.route('/download-resources', methods=['GET'])
def get_public_download_resources():
    """
    获取下载资源列表（公开API）
    可选查询参数：
    - package_type: 包类型 (msi/msix)，不传则返回所有
    """
    package_type = request.args.get('package_type')
    
    # 验证package_type参数
    if package_type and package_type not in ['msi', 'msix']:
        return jsonify({
            "code": 1,
            "message": "Invalid package_type, must be 'msi' or 'msix'",
            "data": None
        }), 400
    
    # 只返回激活的资源
    resources = get_download_resources(package_type=package_type, is_active=True)
    
    return jsonify({
        "code": 0,
        "message": "success",
        "data": resources
    })


@download_resource_bp.route('/download-resources/latest', methods=['GET'])
def get_latest_download_resource():
    """
    获取最新版本（公开API）
    可选查询参数：
    - package_type: 包类型 (msi/msix)，不传则返回最新的任意类型
    """
    package_type = request.args.get('package_type')
    
    # 验证package_type参数
    if package_type and package_type not in ['msi', 'msix']:
        return jsonify({
            "code": 1,
            "message": "Invalid package_type, must be 'msi' or 'msix'",
            "data": None
        }), 400
    
    resource = get_latest_version(package_type=package_type)
    
    if resource:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": resource
        })
    else:
        return jsonify({
            "code": 1,
            "message": "No resource found",
            "data": None
        }), 404


# Web管理端API - 增删改查

@download_resource_bp.route('/web-api/download-resources', methods=['POST'])
@require_maintainer_permission
def web_api_create_download_resource():
    """创建下载资源"""
    data = request.get_json()
    
    # 验证必需字段
    required_fields = ['version', 'package_type', 'download_url']
    if not all(k in data for k in required_fields):
        return jsonify({
            "code": 1,
            "message": f"Missing required fields: {', '.join(required_fields)}",
            "data": None
        }), 400
    
    # 验证package_type
    if data['package_type'] not in ['msi', 'msix']:
        return jsonify({
            "code": 1,
            "message": "Invalid package_type, must be 'msi' or 'msix'",
            "data": None
        }), 400
    
    # 添加创建者信息
    data['created_by'] = str(request.current_user['_id'])
    
    # 创建资源
    resource_id = create_download_resource(data)
    
    if resource_id:
        logger.info(f"Download resource created with ID: {resource_id} by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Download resource created successfully",
            "data": {
                "id": str(resource_id)
            }
        })
    else:
        logger.error("Failed to create download resource")
        return jsonify({
            "code": 2,
            "message": "Failed to create download resource",
            "data": None
        }), 500


@download_resource_bp.route('/web-api/download-resources', methods=['GET'])
@require_maintainer_permission
def web_api_get_download_resources():
    """获取下载资源列表（管理端，包含所有资源，包括未激活的）"""
    package_type = request.args.get('package_type')
    is_active_str = request.args.get('is_active')
    
    # 验证package_type参数
    if package_type and package_type not in ['msi', 'msix']:
        return jsonify({
            "code": 1,
            "message": "Invalid package_type, must be 'msi' or 'msix'",
            "data": None
        }), 400
    
    # 处理is_active参数
    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() == 'true'
    
    resources = get_download_resources(package_type=package_type, is_active=is_active)
    
    return jsonify({
        "code": 0,
        "message": "success",
        "data": resources
    })


@download_resource_bp.route('/web-api/download-resources/<resource_id>', methods=['GET'])
@require_maintainer_permission
def web_api_get_download_resource(resource_id):
    """获取单个下载资源详情"""
    resource = get_download_resource_by_id(resource_id)
    
    if resource:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": resource
        })
    else:
        return jsonify({
            "code": 1,
            "message": "Resource not found",
            "data": None
        }), 404


@download_resource_bp.route('/web-api/download-resources/<resource_id>', methods=['PUT'])
@require_maintainer_permission
def web_api_update_download_resource(resource_id):
    """更新下载资源"""
    data = request.get_json()
    
    # 检查资源是否存在
    existing_resource = get_download_resource_by_id(resource_id)
    if not existing_resource:
        return jsonify({
            "code": 1,
            "message": "Resource not found",
            "data": None
        }), 404
    
    # 验证package_type（如果提供）
    if 'package_type' in data and data['package_type'] not in ['msi', 'msix']:
        return jsonify({
            "code": 1,
            "message": "Invalid package_type, must be 'msi' or 'msix'",
            "data": None
        }), 400
    
    # 添加更新者信息
    data['updated_by'] = str(request.current_user['_id'])
    
    # 更新资源
    success = update_download_resource(resource_id, data)
    
    if success:
        logger.info(f"Download resource {resource_id} updated by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Download resource updated successfully",
            "data": None
        })
    else:
        logger.error(f"Failed to update download resource {resource_id}")
        return jsonify({
            "code": 2,
            "message": "Failed to update download resource",
            "data": None
        }), 500


@download_resource_bp.route('/web-api/download-resources/<resource_id>', methods=['DELETE'])
@require_maintainer_permission
def web_api_delete_download_resource(resource_id):
    """删除下载资源"""
    # 检查资源是否存在
    existing_resource = get_download_resource_by_id(resource_id)
    if not existing_resource:
        return jsonify({
            "code": 1,
            "message": "Resource not found",
            "data": None
        }), 404
    
    # 删除资源
    success = delete_download_resource(resource_id)
    
    if success:
        logger.info(f"Download resource {resource_id} deleted by user: {request.current_user['email']}")
        return jsonify({
            "code": 0,
            "message": "Download resource deleted successfully",
            "data": None
        })
    else:
        logger.error(f"Failed to delete download resource {resource_id}")
        return jsonify({
            "code": 2,
            "message": "Failed to delete download resource",
            "data": None
        }), 500