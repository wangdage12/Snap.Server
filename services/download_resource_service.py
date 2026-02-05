import datetime
from app.extensions import client, logger
from app.config import Config


def create_download_resource(data):
    """
    创建下载资源
    
    :param data: 包含以下字段的数据
        - version: 版本号
        - package_type: 包类型 (msi/msix)
        - download_url: 下载链接
        - features: 新功能描述
        - file_size: 文件大小 (可选)
        - file_hash: 文件哈希 (可选)
        - is_active: 是否激活 (可选，默认为True)
    :return: 创建的资源ID或None
    """
    try:
        resource_doc = {
            "version": data['version'],
            "package_type": data['package_type'],
            "download_url": data['download_url'],
            "features": data.get('features', ''),
            "file_size": data.get('file_size'),
            "file_hash": data.get('file_hash'),
            "is_active": data.get('is_active', True),
            "created_at": datetime.datetime.utcnow(),
            "created_by": data.get('created_by')
        }
        
        result = client.ht_server.download_resources.insert_one(resource_doc)
        logger.info(f"Download resource created with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        logger.error(f"Failed to create download resource: {e}")
        return None


def get_download_resources(package_type=None, is_active=None):
    """
    获取下载资源列表
    
    :param package_type: 包类型过滤 (msi/msix)，None表示获取所有
    :param is_active: 是否激活过滤，None表示获取所有
    :return: 资源列表
    """
    try:
        query = {}
        if package_type:
            query['package_type'] = package_type
        if is_active is not None:
            query['is_active'] = is_active
        
        resources = list(client.ht_server.download_resources.find(query, sort=[("created_at", -1)]))
        
        # 移除 _id 字段并转换日期
        result = []
        for r in resources:
            r = dict(r)
            # 转换_id为字符串并存为id字段
            r['id'] = str(r.pop('_id'))
            # 转换datetime为配置时区的ISO格式字符串
            if 'created_at' in r and isinstance(r['created_at'], datetime.datetime):
                dt = r['created_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                r['created_at'] = dt.isoformat()
            if 'updated_at' in r and isinstance(r['updated_at'], datetime.datetime):
                dt = r['updated_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                r['updated_at'] = dt.isoformat()
            result.append(r)
        
        return result
    except Exception as e:
        logger.error(f"Failed to get download resources: {e}")
        return []


def get_download_resource_by_id(resource_id):
    """
    根据ID获取下载资源
    
    :param resource_id: 资源ID
    :return: 资源对象或None
    """
    try:
        from bson import ObjectId
        resource = client.ht_server.download_resources.find_one({"_id": ObjectId(resource_id)})
        
        if resource:
            resource = dict(resource)
            resource.pop('_id', None)
            # 转换datetime为配置时区的ISO格式字符串
            if 'created_at' in resource and isinstance(resource['created_at'], datetime.datetime):
                dt = resource['created_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                resource['created_at'] = dt.isoformat()
            if 'updated_at' in resource and isinstance(resource['updated_at'], datetime.datetime):
                dt = resource['updated_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                resource['updated_at'] = dt.isoformat()
            return resource
        return None
    except Exception as e:
        logger.error(f"Failed to get download resource by ID: {e}")
        return None


def update_download_resource(resource_id, data):
    """
    更新下载资源
    
    :param resource_id: 资源ID
    :param data: 要更新的字段
    :return: 是否成功
    """
    try:
        from bson import ObjectId
        
        # 构建更新数据
        update_data = {"updated_at": datetime.datetime.utcnow()}
        
        if 'version' in data:
            update_data['version'] = data['version']
        if 'package_type' in data:
            update_data['package_type'] = data['package_type']
        if 'download_url' in data:
            update_data['download_url'] = data['download_url']
        if 'features' in data:
            update_data['features'] = data['features']
        if 'file_size' in data:
            update_data['file_size'] = data['file_size']
        if 'file_hash' in data:
            update_data['file_hash'] = data['file_hash']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        if 'updated_by' in data:
            update_data['updated_by'] = data['updated_by']
        
        result = client.ht_server.download_resources.update_one(
            {"_id": ObjectId(resource_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Download resource {resource_id} updated successfully")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update download resource: {e}")
        return False


def delete_download_resource(resource_id):
    """
    删除下载资源
    
    :param resource_id: 资源ID
    :return: 是否成功
    """
    try:
        from bson import ObjectId
        result = client.ht_server.download_resources.delete_one({"_id": ObjectId(resource_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Download resource {resource_id} deleted successfully")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete download resource: {e}")
        return False


def get_latest_version(package_type=None):
    """
    获取最新版本
    
    :param package_type: 包类型 (msi/msix)，None表示获取所有类型的最新版本
    :return: 资源对象或None
    """
    try:
        query = {"is_active": True}
        if package_type:
            query['package_type'] = package_type
        
        resource = client.ht_server.download_resources.find_one(
            query,
            sort=[("created_at", -1)]
        )
        
        if resource:
            resource = dict(resource)
            resource.pop('_id', None)
            # 转换datetime为配置时区的ISO格式字符串
            if 'created_at' in resource and isinstance(resource['created_at'], datetime.datetime):
                dt = resource['created_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                resource['created_at'] = dt.isoformat()
            if 'updated_at' in resource and isinstance(resource['updated_at'], datetime.datetime):
                dt = resource['updated_at'].replace(tzinfo=datetime.timezone.utc)
                dt = dt.astimezone(Config.TIMEZONE)
                resource['updated_at'] = dt.isoformat()
            return resource
        return None
    except Exception as e:
        logger.error(f"Failed to get latest version: {e}")
        return None