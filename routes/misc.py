from flask import Blueprint, request, jsonify, send_file
from app.extensions import logger, client
from app.config import Config

misc_bp = Blueprint("misc", __name__)


@misc_bp.route('/patch/hutao', methods=['GET'])
def patch_hutao():
    """获取新版本信息"""
    return {
        "code": 0,
        "message": "OK",
        "data": {
            "validation": "",
            "version": "1.0.0",
            "mirrors": []
        }
    }


@misc_bp.route('/git-repository/all', methods=['GET'])
def git_repository_all():
    """获取所有Git仓库"""
    if Config.ISTEST_MODE:
        # 覆盖元数据仓库列表，测试用
        repositories = [
            {
                "name": "test",
                "https_url": "http://server.wdg.cloudns.ch:3000/wdg1122/Snap.Metadata.Test.git",
                "web_url": "http://server.wdg.cloudns.ch:3000/wdg1122/Snap.Metadata.Test",
                "type": "Public"
            }
        ]
        return jsonify({
            "code": 0,
            "message": "OK",
            "data": repositories
        })
    
    # 从数据库获取 Git 仓库列表
    git_repositories = list(client.ht_server.git_repository.find({}))
    
    for repo in git_repositories:
        repo.pop('_id', None)
    
    logger.debug(f"Git repositories: {git_repositories}")
    
    return jsonify({
        "code": 0,
        "message": "OK",
        "data": git_repositories
    })


@misc_bp.route('/static/raw/<category>/<fileName>', methods=['GET'])
def get_image(category, fileName):
    """获取图片资源，弃用，请使用额外的文件服务器"""
    return jsonify({"code": 1, "message": "Image not found"}), 404


@misc_bp.route('/mgnt/am-i-banned', methods=['GET'])
def mgnt_am_i_banned():
    """检查游戏账户是否禁用注入，目前直接返回成功的响应即可"""
    return jsonify({
        "retcode": 0,
        "message": "OK",
        "data": {}
    })
    
# 获取额外的第三方注入工具
@misc_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取额外的第三方注入工具列表"""
    tools = list(client.ht_server.tools.find({}))
    
    for tool in tools:
        tool.pop('_id', None)
    
    logger.debug(f"Tools: {tools}")
    
    return jsonify({
        "code": 0,
        "message": "OK",
        "data": tools
    })