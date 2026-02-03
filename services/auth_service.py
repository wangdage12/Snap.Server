from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import client, logger
from app.config import Config
from app.config_loader import config_loader
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from datetime import timezone
from zoneinfo import ZoneInfo
import datetime
import SendEmailTool
import re
import base64

def decrypt_data(encrypted_data: str) -> str:
    """使用RSA私钥解密数据"""
    try:
        private_key_file = config_loader.RSA_PRIVATE_KEY_FILE
        with open(private_key_file, 'r') as f:
            private_key = RSA.import_key(f.read())
        cipher = PKCS1_OAEP.new(private_key)
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise


def send_verification_email(email: str, code: str, ACTION_NAME="注册", EXPIRE_MINUTES=None) -> bool:
    """发送验证码邮件，目前只有注册场景，后续再扩展其他场景"""
    try:
        subject = Config.EMAIL_SUBJECT
        textbody = f"您的验证码是: {code}"
        APP_NAME = Config.EMAIL_APP_NAME
        OFFICIAL_WEBSITE = Config.EMAIL_OFFICIAL_WEBSITE
        if EXPIRE_MINUTES is None:
            EXPIRE_MINUTES = Config.VERIFICATION_CODE_EXPIRE_MINUTES
        htmlbody = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>验证码邮件</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f6f7;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 0;">
        <!-- 主体卡片 -->
        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:32px;">
          
          <!-- 应用名 -->
          <tr>
            <td align="center" style="font-size:22px;font-weight:bold;color:#333333;padding-bottom:16px;">
              {APP_NAME}
            </td>
          </tr>

          <!-- 操作提示 -->
          <tr>
            <td style="font-size:14px;color:#555555;padding-bottom:24px;text-align:center;">
              你正在进行 <strong>{ACTION_NAME}</strong> 操作，请使用以下验证码完成验证：
            </td>
          </tr>

          <!-- 验证码 -->
          <tr>
            <td align="center" style="padding:20px 0;">
              <div style="
                display:inline-block;
                font-size:32px;
                font-weight:bold;
                letter-spacing:6px;
                color:#2e86de;
                padding:12px 24px;
                border:1px dashed #2e86de;
                border-radius:6px;
              ">
                {code}
              </div>
            </td>
          </tr>

          <!-- 有效期说明 -->
          <tr>
            <td style="font-size:13px;color:#888888;text-align:center;padding-top:16px;">
              验证码有效期 {EXPIRE_MINUTES} 分钟，请勿泄露给他人。
            </td>
          </tr>

          <!-- 分割线 -->
          <tr>
            <td style="padding:24px 0;">
              <hr style="border:none;border-top:1px solid #eeeeee;">
            </td>
          </tr>

          <!-- 底部信息 -->
          <tr>
            <td style="font-size:12px;color:#999999;text-align:center;line-height:1.6;">
              本邮件由 {APP_NAME} 系统自动发送，请勿回复<br>
              如非本人操作，请忽略本邮件
            </td>
          </tr>

          <!-- 官网链接 -->
          <tr>
            <td align="center" style="padding-top:16px;">
              <a href="{OFFICIAL_WEBSITE}" 
                 style="font-size:12px;color:#2e86de;text-decoration:none;">
                访问官网
              </a>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>

        """
        try:
            SendEmailTool.send_email(
                config_loader.EMAIL_GMAIL_USER,
                config_loader.EMAIL_APP_PASSWORD,
                email,
                subject,
                htmlbody,
                app_name=APP_NAME,
                body_type="html"
            )
            logger.info(f"HTML Verification email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send HTML verification email to {email}: {e}")
            # 如果 HTML 邮件发送失败，尝试发送纯文本邮件
            SendEmailTool.send_email(
                config_loader.EMAIL_GMAIL_USER,
                config_loader.EMAIL_APP_PASSWORD,
                email,
                subject,
                textbody,
                app_name=APP_NAME,
                body_type="plain"
            )
            logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def verify_user_credentials(email: str, password: str) -> dict | None:
    """验证用户凭据"""
    user = client.ht_server.users.find_one({"email": email})
    
    if not user or not check_password_hash(user['password'], password):
        return None
    
    return user


def create_user_account(email: str, password: str) -> dict | None:
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
        # 现在默认用户的上传权限不过期
        "GachaLogExpireAt": "2099-01-01T00:00:00Z",
        "CdnExpireAt": "2099-01-01T00:00:00Z"
    }
    
    result = client.ht_server.users.insert_one(new_user)
    new_user['_id'] = result.inserted_id
    
    return new_user


def get_user_by_id(user_id: str) -> dict | None:
    """根据ID获取用户信息"""
    try:
        user = client.ht_server.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by ID: {e}")
        return None


def get_users_with_search(query_text="") -> list:
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

        query = {"$or": or_conditions}

    # 查询数据库（排除密码）
    cursor = client.ht_server.users.find(query, {"password": 0})

    # 去重（按 _id）
    users_map = {}
    for u in cursor:
        users_map[str(u["_id"])] = u

    users = list(users_map.values())

    # 数据格式化
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