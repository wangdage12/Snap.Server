from app.extensions import client, logger
from app.config import Config

def get_announcements(request_data: list):
    """
    获取公告列表，过滤掉用户已关闭的公告
    
    :param request_data: 用户已关闭的公告ID列表
    :type request_data: list
    """
    if Config.ISTEST_MODE:
        return []
    # 记录请求体到日志，请求体中是用户已关闭的公告ID列表
    logger.debug("Request body: %s", request_data)

    announcements = list(client.ht_server.announcement.find({}))
    result = []
    for a in announcements:
        # 拷贝并移除 _id 字段，避免 ObjectId 无法序列化
        a = dict(a)
        a.pop('_id', None)
        # 如果请求体中包含该公告ID，说明用户已关闭该公告，不返回该公告
        if a.get('Id') not in request_data:
            result.append(a)
    return result
