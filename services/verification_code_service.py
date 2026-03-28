import datetime
from app.extensions import client, logger

REGISTRATION_REQUEST_TYPE = 0b0000
RESET_PASSWORD_REQUEST_TYPE = 0b0001
CANCEL_REGISTRATION_REQUEST_TYPE = 0b0010
RESET_USERNAME_REQUEST_TYPE = 0b0100
RESET_USERNAME_NEW_REQUEST_TYPE = 0b1000

VERIFICATION_CODE_TYPE_METADATA = {
    REGISTRATION_REQUEST_TYPE: {
        "action_name": "注册",
        "display_name": "注册",
        "requires_existing_user": False,
        "requires_available_email": True,
    },
    RESET_PASSWORD_REQUEST_TYPE: {
        "action_name": "修改密码",
        "display_name": "修改密码",
        "requires_existing_user": True,
        "requires_available_email": False,
    },
    CANCEL_REGISTRATION_REQUEST_TYPE: {
        "action_name": "注销账号",
        "display_name": "注销账号",
        "requires_existing_user": True,
        "requires_available_email": False,
    },
    RESET_USERNAME_REQUEST_TYPE: {
        "action_name": "修改邮箱",
        "display_name": "修改邮箱（原邮箱验证）",
        "requires_existing_user": True,
        "requires_available_email": False,
    },
    RESET_USERNAME_NEW_REQUEST_TYPE: {
        "action_name": "修改邮箱",
        "display_name": "修改邮箱（新邮箱验证）",
        "requires_existing_user": False,
        "requires_available_email": True,
    },
}


def parse_verification_type(raw_type, default=REGISTRATION_REQUEST_TYPE) -> int | None:
    if raw_type in (None, ""):
        return default

    try:
        request_type = int(raw_type)
    except (TypeError, ValueError):
        return None

    return request_type if request_type in VERIFICATION_CODE_TYPE_METADATA else None


def get_verification_type_metadata(request_type: int) -> dict | None:
    return VERIFICATION_CODE_TYPE_METADATA.get(request_type)


def init_verification_code_collection():
    """初始化验证码集合并创建所需索引"""
    db = client.ht_server
    collection = db.verification_codes

    indexes = {index.get('name') for index in collection.list_indexes()}

    if 'expire_at_ttl' not in indexes:
        collection.create_index(
            [("expire_at", 1)],
            expireAfterSeconds=0,
            name="expire_at_ttl"
        )
        logger.info("Created TTL index on verification_codes collection")

    if 'email_type_created_at_idx' not in indexes:
        collection.create_index(
            [("email", 1), ("request_type", 1), ("created_at", -1)],
            name="email_type_created_at_idx"
        )


def save_verification_code(email: str, code: str, request_type: int = REGISTRATION_REQUEST_TYPE, expire_minutes: int = 10):
    """保存验证码到 MongoDB，自动过期时间由 TTL 索引控制"""
    db = client.ht_server
    collection = db.verification_codes

    init_verification_code_collection()

    now = datetime.datetime.utcnow()
    expire_at = now + datetime.timedelta(minutes=expire_minutes)
    metadata = get_verification_type_metadata(request_type) or {}

    collection.delete_many({
        "email": email,
        "request_type": request_type,
    })

    result = collection.insert_one({
        "email": email,
        "code": code,
        "request_type": request_type,
        "request_type_name": metadata.get("display_name", str(request_type)),
        "created_at": now,
        "expire_at": expire_at,
        "used": False,
    })

    logger.debug(f"Saved verification code for email: {email}, request_type: {request_type}")
    return result.inserted_id


def get_valid_verification_code(email: str, code: str, request_type: int = REGISTRATION_REQUEST_TYPE) -> dict | None:
    db = client.ht_server
    collection = db.verification_codes
    now = datetime.datetime.utcnow()

    verification_record = collection.find_one({
        "email": email,
        "code": code,
        "request_type": request_type,
        "used": False,
        "expire_at": {"$gt": now},
    }, sort=[("created_at", -1)])

    if verification_record:
        return verification_record

    collection.delete_many({
        "email": email,
        "code": code,
        "request_type": request_type,
        "expire_at": {"$lte": now},
    })
    return None


def delete_verification_code(record_id) -> bool:
    db = client.ht_server
    collection = db.verification_codes
    result = collection.delete_one({"_id": record_id})
    return result.deleted_count > 0


def delete_verification_codes(emails: list[str], request_types: list[int] | None = None) -> int:
    db = client.ht_server
    collection = db.verification_codes
    normalized_emails = [email for email in emails if email]
    if not normalized_emails:
        return 0

    query = {"email": {"$in": normalized_emails}}
    if request_types:
        query["request_type"] = {"$in": request_types}

    result = collection.delete_many(query)
    return result.deleted_count


def verify_code(email: str, code: str, request_type: int = REGISTRATION_REQUEST_TYPE) -> bool:
    """验证验证码是否正确，验证成功后删除验证码记录"""
    db = client.ht_server
    collection = db.verification_codes
    now = datetime.datetime.utcnow()

    verification_record = collection.find_one_and_delete({
        "email": email,
        "code": code,
        "request_type": request_type,
        "used": False,
        "expire_at": {"$gt": now},
    }, sort=[("created_at", -1)])

    if verification_record:
        logger.info(f"Verification code validated and deleted for email: {email}, request_type: {request_type}")
        return True

    collection.delete_many({
        "email": email,
        "code": code,
        "request_type": request_type,
        "expire_at": {"$lte": now},
    })
    logger.warning(f"Invalid or expired verification code for email: {email}, request_type: {request_type}")
    return False
