import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import client, logger
from app.config import Config


def decrypt_data(encrypted_data):
    """使用RSA私钥解密数据"""
    try:
        from Crypto.Cipher import PKCS1_OAEP
        from Crypto.PublicKey import RSA
        import base64
        from app.config_loader import config_loader
        
        private_key_file = config_loader.RSA_PRIVATE_KEY_FILE
        private_key = RSA.import_key(open(private_key_file).read())
        cipher = PKCS1_OAEP.new(private_key)
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise


def send_verification_email(email, code):
    """发送验证码邮件"""
    try:
        import SendEmailTool
        
        subject = "Snap Hutao 验证码"
        body = f"您的验证码是: {code}"
        
        SendEmailTool.send_email(
            SendEmailTool.gmail_user,
            SendEmailTool.app_password,
            email,
            subject,
            body
        )
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def verify_user_credentials(email, password):
    """验证用户凭据"""
    user = client.ht_server.users.find_one({"email": email})
    
    if not user or not check_password_hash(user['password'], password):
        return None
    
    return user


def create_user_account(email, password):
    """创建新用户账户"""
    # 检查用户是否已存在
    existing_user = client.ht_server.users.find_one({"email": email})
    if existing_user:
        return None
    
    # 对密码进行哈希处理
    hashed_password = generate_password_hash(password)
        
    # 创建新用户
    new_user = {
        "email": email,
        "password": hashed_password,
        "NormalizedUserName": email,
        "UserName": email,
        "CreatedAt": datetime.datetime.utcnow(),
        "IsLicensedDeveloper": False,
        "IsMaintainer": False,
        "GachaLogExpireAt": "2026-01-01T00:00:00Z",
        "CdnExpireAt": "2026-01-01T00:00:00Z"
    }
    
    result = client.ht_server.users.insert_one(new_user)
    new_user['_id'] = result.inserted_id
    
    return new_user


def get_user_by_id(user_id):
    """根据ID获取用户信息"""
    try:
        user = client.ht_server.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
        return user
    except:
        return None


def get_users_with_search(query_text=""):
    """获取用户列表，支持搜索"""
    import re
    
    # 构建查询条件
    query = {}
    or_conditions = []

    if query_text:
        # 用户名模糊搜索
        or_conditions.append({
            "UserName": {"$regex": re.escape(query_text), "$options": "i"}
        })

        # 邮箱模糊搜索
        or_conditions.append({
            "email": {"$regex": re.escape(query_text), "$options": "i"}
        })

        # _id 搜索（支持完整或前缀）
        if ObjectId.is_valid(query_text):
            or_conditions.append({
                "_id": ObjectId(query_text)
            })
        else:
            # 允许部分 ObjectId 搜索（转字符串后匹配）
            or_conditions.append({
                "_id": {
                    "$in": [
                        u["_id"] for u in client.ht_server.users.find(
                            {},
                            {"_id": 1}
                        ) if query_text.lower() in str(u["_id"]).lower()
                    ]
                }
            })

        query = {"$or": or_conditions}

    # 查询数据库（排除密码）
    cursor = client.ht_server.users.find(query, {"password": 0})

    # 去重（按 _id）
    users_map = {}
    for u in cursor:
        users_map[str(u["_id"])] = u

    users = list(users_map.values())

    # 数据格式化
    from datetime import timezone
    from zoneinfo import ZoneInfo
    
    CST = ZoneInfo("Asia/Shanghai")
    
    for u in users:
        u['_id'] = str(u['_id'])

        created_at = u.get("CreatedAt")
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            created_at_cst = created_at.astimezone(CST)
            u["CreatedAt"] = created_at_cst.strftime("%Y-%m-%d %H:%M:%S")

    return users