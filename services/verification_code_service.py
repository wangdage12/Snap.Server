import datetime
from app.extensions import client, logger


def init_verification_code_collection():
    """初始化验证码集合并创建 TTL 索引"""
    db = client.ht_server
    collection = db.verification_codes

    indexes = collection.list_indexes()
    ttl_index_exists = False
    for index in indexes:
        if index.get('expireAfterSeconds') is not None:
            ttl_index_exists = True
            break

    # 如果不存在 TTL 索引，则创建
    if not ttl_index_exists:
        collection.create_index(
            [("expire_at", 1)],
            expireAfterSeconds=0,
            name="expire_at_ttl"
        )
        logger.info("Created TTL index on verification_codes collection")


def save_verification_code(email: str, code: str, expire_minutes: int = 10):
    """保存验证码到 MongoDB，自动过期时间由 TTL 索引控制"""
    db = client.ht_server
    collection = db.verification_codes

    # 确保集合已初始化
    init_verification_code_collection()

    # 计算过期时间
    expire_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)

    # 插入验证码记录
    result = collection.insert_one({
        "email": email,
        "code": code,
        "created_at": datetime.datetime.utcnow(),
        "expire_at": expire_at,
        "used": False
    })

    logger.debug(f"Saved verification code for email: {email}")
    return result.inserted_id


def verify_code(email: str, code: str) -> bool:
    """验证验证码是否正确，验证成功后删除验证码记录"""
    db = client.ht_server
    collection = db.verification_codes

    # 查找未使用的验证码
    verification_record = collection.find_one({
        "email": email,
        "code": code,
        "used": False
    })

    if verification_record:
        # 验证成功，删除该验证码记录
        collection.delete_one({"_id": verification_record["_id"]})
        logger.info(f"Verification code validated and deleted for email: {email}")
        return True

    logger.warning(f"Invalid or expired verification code for email: {email}")
    return False