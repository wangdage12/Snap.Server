from flask import Blueprint, request, jsonify, send_file
from app.extensions import logger, client
from app.config import Config

misc_bp = Blueprint("misc", __name__)


def _get_client_ip() -> str:
    """获取客户端 IP，优先取反向代理头。"""
    forwarded_for = request.headers.get('X-Forwarded-For', '').strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    real_ip = request.headers.get('X-Real-IP', '').strip()
    if real_ip:
        return real_ip

    return request.remote_addr or ''


@misc_bp.route('/ip', methods=['GET'])
def get_ip_information():
    """获取当前网络 IP 信息。"""
    return jsonify({
        "retcode": 0,
        "message": "OK",
        "data": {
            "ip": _get_client_ip(),
            "division": ""
        },
        "l10nKey": None
    })


@misc_bp.route('/Statistics/Avatar/AvatarCollocation', methods=['GET'])
def statistics_avatar_avatar_collocation():
    """获取角色搭配统计，当前返回空列表。"""
    return jsonify({
        "retcode": 0,
        "message": "OK",
        "data": [],
        "l10nKey": None
    })


@misc_bp.route('/Statistics/Weapon/WeaponCollocation', methods=['GET'])
def statistics_weapon_weapon_collocation():
    """获取武器搭配统计，当前返回空列表。"""
    return jsonify({
        "retcode": 0,
        "message": "OK",
        "data": [],
        "l10nKey": None
    })


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
        # 添加默认字段，用于客户端解压、确定运行exe和版本更新检查
        if 'is_compressed' not in tool:
            tool['is_compressed'] = False
        if 'version' not in tool:
            tool['version'] = '1.0.0'
        if 'main_exe' not in tool:
            tool['main_exe'] = None
    
    logger.debug(f"Tools: {tools}")
    
    return jsonify({
        "code": 0,
        "message": "OK",
        "data": tools
    })