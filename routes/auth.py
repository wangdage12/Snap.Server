from flask import Blueprint, request, jsonify
from app.utils.jwt_utils import create_token, verify_token
from services.auth_service import (
    decrypt_data, send_verification_email, verify_user_credentials,
    create_user_account, get_user_by_id
)
from services.verification_code_service import save_verification_code, verify_code
from app.extensions import generate_code, logger , config_loader
from app.config import Config

auth_bp = Blueprint("auth", __name__)


@auth_bp.route('/Passport/v2/Verify', methods=['POST'])
def passport_verify():
    """获取验证码"""
    data = request.get_json()
    encrypted_email = data.get('UserName', '')

    try:
        decrypted_email = decrypt_data(encrypted_email)
        logger.debug(f"Decrypted email: {decrypted_email}")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return jsonify({
            "retcode": 1,
            "message": f"Invalid encrypted email: {str(e)}",
            "data": None
        })

    # 生成验证码
    code = generate_code(6)
    # 使用 MongoDB TTL 存储验证码
    save_verification_code(decrypted_email, code, expire_minutes=Config.VERIFICATION_CODE_EXPIRE_MINUTES)

    # 发送邮件
    if send_verification_email(decrypted_email, code):
        return jsonify({
            "retcode": 0,
            "message": "success",
            "l10nKey": "ViewDialogUserAccountVerificationEmailCaptchaSent"
        })
    else:
        return jsonify({
            "retcode": 1,
            "message": "Failed to send email",
            "data": None
        }), 500


@auth_bp.route('/Passport/v2/Register', methods=['POST'])
def passport_register():
    """用户注册"""
    data = request.get_json()
    encrypted_email = data.get('UserName', '')
    encrypted_password = data.get('Password', '')
    encrypted_code = data.get('VerifyCode', '')

    try:
        decrypted_email = decrypt_data(encrypted_email)
        decrypted_password = decrypt_data(encrypted_password)
        decrypted_code = decrypt_data(encrypted_code)

        logger.debug(f"Decrypted registration data: email={decrypted_email}, code={decrypted_code}")
    except Exception as e:
        logger.warning(f"Decryption error: {e}")
        return jsonify({
            "retcode": 1,
            "message": f"Invalid encrypted data: {str(e)}",
            "data": None
        }), 400

    # 使用 MongoDB 验证验证码
    if not verify_code(decrypted_email, decrypted_code):
        logger.warning("Invalid verification code")
        return jsonify({
            "retcode": 2,
            "message": "Invalid verification code",
            "data": None
        })

    # 创建新用户
    new_user = create_user_account(decrypted_email, decrypted_password)
    if not new_user:
        logger.warning(f"User already exists: {decrypted_email}")
        return jsonify({
            "retcode": 3,
            "message": "User already exists",
            "data": None
        })

    # 创建token
    access_token = create_token(str(new_user['_id']))
    logger.info(f"User registered: {decrypted_email}")

    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": access_token,
            "ExpiresIn": config_loader.JWT_EXPIRATION_HOURS * 3600
        }
    })


@auth_bp.route('/Passport/v2/Login', methods=['POST'])
def passport_login():
    """用户登录"""
    data = request.get_json()
    encrypted_email = data.get('UserName', '')
    encrypted_password = data.get('Password', '')
    
    try:
        decrypted_email = decrypt_data(encrypted_email)
        decrypted_password = decrypt_data(encrypted_password)
        
        logger.debug(f"Decrypted login data: email={decrypted_email}")
    except Exception as e:
        logger.warning(f"Decryption error: {e}")
        return jsonify({
            "retcode": 1,
            "message": f"Invalid encrypted data: {str(e)}",
            "data": None
        }), 400
    
    # 验证用户凭据
    user = verify_user_credentials(decrypted_email, decrypted_password)
    if not user:
        logger.warning(f"Invalid login attempt for email: {decrypted_email}")
        return jsonify({
            "retcode": 2,
            "message": "Invalid email or password",
            "data": None
        })
    
    # 创建token
    access_token = create_token(str(user['_id']))
    logger.info(f"User logged in: {decrypted_email}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "l10nKey": "ServerPassportLoginSucceed",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": access_token,
            "ExpiresIn": config_loader.JWT_EXPIRATION_HOURS * 3600
        }
    })


@auth_bp.route('/Passport/v2/UserInfo', methods=['GET'])
def passport_userinfo():
    """获取用户信息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired token",
            "data": None
        }), 401
    
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"User not found: {user_id}")
        return jsonify({
            "retcode": 2,
            "message": "User not found",
            "data": None
        })
    
    logger.info(f"User info retrieved: {user['email']}")
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {
            "NormalizedUserName": user['NormalizedUserName'],
            "UserName": user['UserName'],
            "IsLicensedDeveloper": user['IsLicensedDeveloper'],
            "IsMaintainer": user['IsMaintainer'],
            "GachaLogExpireAt": user['GachaLogExpireAt'],
            "CdnExpireAt": user['CdnExpireAt']
        }
    })


@auth_bp.route('/Passport/v2/RefreshToken', methods=['POST'])
def passport_refresh_token():
    """刷新Token"""
    data = request.get_json()
    refresh_token = data.get('RefreshToken', '')
    
    try:
        decrypted_refresh_token = decrypt_data(refresh_token)
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return jsonify({
            "retcode": 1,
            "message": f"Invalid encrypted refresh token: {str(e)}",
            "data": None
        }), 400
    
    user_id = verify_token(decrypted_refresh_token)
    if not user_id:
        logger.warning("Invalid or expired refresh token")
        return jsonify({
            "retcode": 1,
            "message": "Invalid or expired refresh token",
            "data": None
        })
    
    access_token = create_token(user_id)
    logger.info(f"Token refreshed for user_id: {user_id}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": access_token,
            "ExpiresIn": config_loader.JWT_EXPIRATION_HOURS * 3600
        }
    })


@auth_bp.route('/Passport/v2/RevokeToken', methods=['POST'])
def passport_revoke_token():
    """注销Token"""
    logger.info("Token revoked")
    return jsonify({
        "retcode": 0,
        "message": "Token revoked successfully",
        "data": None
    })