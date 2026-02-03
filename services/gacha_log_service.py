from app.extensions import client, logger

"""
注意！记录中有两种类型，GachaType和QueryType(uigf_gacha_type)，GachaType多了一个400类型，其实就是QueryType的301类型，客户端传的end_ids是按QueryType来的，如果按照GachaType来筛选会多出400类型的记录
映射关系

| `uigf_gacha_type` | `gacha_type`   |
|-------------------|----------------|
| `100`             | `100`          |
| `200`             | `200`          |
| `301`             | `301` or `400` |
| `302`             | `302`          |
| `500`             | `500`          |
"""

def get_gacha_log_entries(user_id):
    """获取用户的祈愿记录条目列表"""
    gacha_logs = list(client.ht_server.GachaLog.find({"user_id": user_id}))
    entries = []
    for log in gacha_logs:
        entry = {
            "Uid": log['Uid'],
            "Excluded": False,
            "ItemCount": len(log['data'])
        }
        entries.append(entry)
    return entries


def get_gacha_log_end_ids(user_id, uid):
    """获取指定 UID 用户的祈愿记录最新 ID"""
    gacha_log = client.ht_server.GachaLog.find_one({"user_id": user_id, "Uid": uid})
    if not gacha_log:
        return {
            "100": 0,  # NoviceWish
            "200": 0,  # StandardWish
            "301": 0,  # AvatarEventWish
            "302": 0,  # WeaponEventWish
            "500": 0   # ChronicledWish
        }
    
    # 计算各个祈愿类型的最新ID
    end_ids = {
        "100": 0,
        "200": 0,
        "301": 0,
        "302": 0,
        "500": 0
    }
    for item in gacha_log['data']:
        gacha_type = str(item.get('GachaType', ''))
        item_id = item.get('Id', 0)
        if gacha_type in end_ids:
            end_ids[gacha_type] = max(end_ids[gacha_type], item_id)
    
    # 400类型对应301类型
    end_ids["400"] = end_ids["301"]
    
    return end_ids


def upload_gacha_log(user_id, uid, items):
    """上传祈愿记录"""
    # 查找是否已有该用户和UID的祈愿记录
    existing_log = client.ht_server.GachaLog.find_one({"user_id": user_id, "Uid": uid})
    
    if existing_log:
        # 已有数据，合并新旧数据（按Id去重）
        old_items = existing_log.get('data', [])
        # 用Id做索引，先加旧的，再加新的（新数据覆盖旧数据）
        item_dict = {item.get('Id'): item for item in old_items}
        for item in items:
            item_dict[item.get('Id')] = item
        merged_items = list(item_dict.values())
        # 更新数据库
        client.ht_server.GachaLog.update_one(
            {"_id": existing_log['_id']},
            {"$set": {"data": merged_items}}
        )
        return f"success, merged {len(items)} new items, total {len(merged_items)} items"
    else:
        # 没有数据，直接插入
        gacha_log_entry = {
            "user_id": user_id,
            "Uid": uid,
            "data": items
        }
        client.ht_server.GachaLog.insert_one(gacha_log_entry)
        return f"success, uploaded {len(items)} items"


def retrieve_gacha_log(user_id, uid, end_ids):
    """从云端检索用户的祈愿记录数据"""
    gacha_log = client.ht_server.GachaLog.find_one({"user_id": user_id, "Uid": uid})
    if not gacha_log:
        return []
    
    # 筛选出比end_ids更旧的记录
    filtered_items = []
    
    # 需要将end_ids的key从QueryType转换为GachaType，给400赋值为301的值即可
    if "301" in end_ids:
        end_ids["400"] = end_ids["301"]
    
    for item in gacha_log['data']:
        gacha_type = str(item.get('GachaType', ''))
        item_id = item.get('Id', 0)
        # end_ids有可能是0，那么返回全部
        if (gacha_type in end_ids and item_id < end_ids[gacha_type]) or end_ids.get(gacha_type, 0) == 0:
            filtered_items.append(item)
    
    return filtered_items


def delete_gacha_log(user_id, uid):
    """删除指定用户的祈愿记录"""
    result = client.ht_server.GachaLog.delete_one({"user_id": user_id, "Uid": uid})
    return result.deleted_count > 0