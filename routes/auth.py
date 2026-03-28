from flask import Blueprint, request, jsonify
from app.utils.jwt_utils import create_token, verify_token, create_refresh_token
from services.auth_service import (
    decrypt_data, send_verification_email, verify_user_credentials,
    create_user_account, get_user_by_id, get_user_by_email,
    update_user_password, update_user_email, delete_user_account
)
from services.verification_code_service import (
    REGISTRATION_REQUEST_TYPE,
    RESET_PASSWORD_REQUEST_TYPE,
    CANCEL_REGISTRATION_REQUEST_TYPE,
    RESET_USERNAME_REQUEST_TYPE,
    RESET_USERNAME_NEW_REQUEST_TYPE,
    parse_verification_type,
    get_verification_type_metadata,
    save_verification_code,
    get_valid_verification_code,
    delete_verification_code,
    delete_verification_codes,
    verify_code,
)
from app.extensions import generate_code, logger , config_loader
from app.config import Config

auth_bp = Blueprint("auth", __name__)


def hutao_response(retcode: int, message: str, data=None, l10n_key=None, status_code: int = 200):
    return jsonify({
        "retcode": retcode,
        "message": message,
        "data": data,
        "l10nKey": l10n_key,
    }), status_code


def build_token_set(user_id: str) -> dict:
    return {
        "AccessToken": create_token(user_id),
        "RefreshToken": create_refresh_token(user_id),
        "ExpiresIn": config_loader.JWT_EXPIRATION_HOURS * 3600,
    }


def is_enabled_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == 'true'
    if isinstance(value, (int, float)):
        return value != 0
    return False


def resolve_verify_request_type(data: dict) -> int | None:
    flag_mapping = [
        ('IsResetPassword', RESET_PASSWORD_REQUEST_TYPE),
        ('IsCancelRegistration', CANCEL_REGISTRATION_REQUEST_TYPE),
        ('IsResetUserName', RESET_USERNAME_REQUEST_TYPE),
        ('IsResetUserNameNew', RESET_USERNAME_NEW_REQUEST_TYPE),
    ]

    enabled_request_types = [
        request_type
        for field_name, request_type in flag_mapping
        if is_enabled_flag(data.get(field_name))
    ]

    if len(enabled_request_types) > 1:
        return None

    if len(enabled_request_types) == 1:
        return enabled_request_types[0]

    raw_request_type = data.get('Type')
    if raw_request_type in (None, ''):
        raw_request_type = data.get('VerifyCodeRequestType')
    if raw_request_type in (None, ''):
        raw_request_type = data.get('RequestType')
    return parse_verification_type(raw_request_type, default=REGISTRATION_REQUEST_TYPE)


@auth_bp.route('/Passport/v2/Verify', methods=['POST'])
def passport_verify():
    """获取验证码"""
    data = request.get_json(silent=True) or {}
    encrypted_email = data.get('UserName', '')
    request_type = resolve_verify_request_type(data)

    if request_type is None:
        return hutao_response(
            2,
            "验证码类型无效\nInvalid verification code type",
            status_code=400,
        )

    try:
        decrypted_email = decrypt_data(encrypted_email)
        logger.debug(f"Decrypted email: {decrypted_email}, request_type: {request_type}")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return hutao_response(
            1,
            f"解密邮件地址失败: {str(e)}",
            status_code=400,
        )

    metadata = get_verification_type_metadata(request_type)

    code = generate_code(6)
    save_verification_code(
        decrypted_email,
        code,
        request_type=request_type,
        expire_minutes=Config.VERIFICATION_CODE_EXPIRE_MINUTES,
    )

    if send_verification_email(
        decrypted_email,
        code,
        ACTION_NAME=metadata["action_name"],
        EXPIRE_MINUTES=Config.VERIFICATION_CODE_EXPIRE_MINUTES,
        REQUEST_TYPE=request_type,
        TYPE_LABEL=metadata["display_name"],
    ):
        return hutao_response(
            0,
            "success",
            l10n_key="ViewDialogUserAccountVerificationEmailCaptchaSent",
        )

    return hutao_response(
        5,
        "发送验证码邮件失败\nsend verification email failed",
        status_code=500,
    )


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
            "message": f"解密注册数据失败: {str(e)}",
            "data": None
        }), 400

    # 使用 MongoDB 验证验证码
    if not verify_code(decrypted_email, decrypted_code, request_type=REGISTRATION_REQUEST_TYPE):
        logger.warning("Invalid verification code")
        return jsonify({
            "retcode": 2,
            "message": "验证码无效或已过期\nInvalid or expired verification code",
            "data": None
        })

    # 创建新用户
    new_user = create_user_account(decrypted_email, decrypted_password)
    if not new_user:
        logger.warning(f"User already exists: {decrypted_email}")
        return jsonify({
            "retcode": 3,
            "message": "用户已存在\nUser already exists",
            "data": None
        })

    # 创建token
    access_token = create_token(str(new_user['_id']))
    # 刷新token
    refresh_token = create_refresh_token(str(new_user['_id']))
    logger.info(f"User registered: {decrypted_email}")

    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": refresh_token,
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
            "message": f"解密登录数据失败: {str(e)}",
            "data": None
        }), 400
    
    # 验证用户凭据
    user = verify_user_credentials(decrypted_email, decrypted_password)
    if not user:
        logger.warning(f"Invalid login attempt for email: {decrypted_email}")
        return jsonify({
            "retcode": 2,
            "message": "邮箱或密码无效\nInvalid email or password",
            "data": None
        })
    
    # 创建token
    access_token = create_token(str(user['_id']))
    refresh_token = create_refresh_token(str(user['_id']))
    logger.info(f"User logged in: {decrypted_email}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "l10nKey": "ServerPassportLoginSucceed",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": refresh_token,
            "ExpiresIn": config_loader.JWT_EXPIRATION_HOURS * 3600
        }
    })


@auth_bp.route('/Passport/v2/ResetUsername', methods=['POST'])
def passport_reset_username():
    """修改邮箱"""
    data = request.get_json(silent=True) or {}
    encrypted_email = data.get('UserName', '')
    encrypted_new_email = data.get('NewUserName', '')
    encrypted_code = data.get('VerifyCode', '')
    encrypted_new_code = data.get('NewVerifyCode', '')

    try:
        decrypted_email = decrypt_data(encrypted_email)
        decrypted_new_email = decrypt_data(encrypted_new_email)
        decrypted_code = decrypt_data(encrypted_code)
        decrypted_new_code = decrypt_data(encrypted_new_code)
    except Exception as e:
        logger.warning(f"Reset username decryption error: {e}")
        return hutao_response(
            1,
            f"解密修改邮箱数据失败: {str(e)}",
            status_code=400,
        )

    if decrypted_email == decrypted_new_email:
        return hutao_response(
            2,
            "新邮箱不能与旧邮箱相同\nNew email cannot be the same as the current email",
        )

    old_user = get_user_by_email(decrypted_email)
    if not old_user:
        return hutao_response(
            5,
            "用户不存在\nUser not found",
            status_code=404,
        )

    if get_user_by_email(decrypted_new_email):
        return hutao_response(
            6,
            "新邮箱已被占用\nNew email already exists",
        )

    old_code_record = get_valid_verification_code(
        decrypted_email,
        decrypted_code,
        request_type=RESET_USERNAME_REQUEST_TYPE,
    )
    if not old_code_record:
        return hutao_response(
            3,
            "原邮箱验证码无效或已过期\nInvalid or expired verification code for current email",
        )

    new_code_record = get_valid_verification_code(
        decrypted_new_email,
        decrypted_new_code,
        request_type=RESET_USERNAME_NEW_REQUEST_TYPE,
    )
    if not new_code_record:
        return hutao_response(
            4,
            "新邮箱验证码无效或已过期\nInvalid or expired verification code for new email",
        )

    update_status, updated_user = update_user_email(decrypted_email, decrypted_new_email)
    if update_status == "not_found":
        return hutao_response(
            5,
            "用户不存在\nUser not found",
            status_code=404,
        )
    if update_status == "same_email":
        return hutao_response(
            2,
            "新邮箱不能与旧邮箱相同\nNew email cannot be the same as the current email",
        )
    if update_status == "new_email_exists":
        return hutao_response(
            6,
            "新邮箱已被占用\nNew email already exists",
        )
    if update_status != "success" or not updated_user:
        return hutao_response(
            7,
            "修改邮箱失败\nFailed to update email",
            status_code=500,
        )

    if not delete_verification_code(old_code_record['_id']):
        logger.warning(f"Failed to delete current email verification code for {decrypted_email}")
    if not delete_verification_code(new_code_record['_id']):
        logger.warning(f"Failed to delete new email verification code for {decrypted_new_email}")

    logger.info(f"User email updated: {decrypted_email} -> {decrypted_new_email}")
    return hutao_response(
        0,
        "success",
        data=build_token_set(str(updated_user['_id'])),
    )


@auth_bp.route('/Passport/v2/ResetPassword', methods=['POST'])
def passport_reset_password():
    """修改密码"""
    data = request.get_json(silent=True) or {}
    encrypted_email = data.get('UserName', '')
    encrypted_password = data.get('Password', '')
    encrypted_code = data.get('VerifyCode', '')

    try:
        decrypted_email = decrypt_data(encrypted_email)
        decrypted_password = decrypt_data(encrypted_password)
        decrypted_code = decrypt_data(encrypted_code)
    except Exception as e:
        logger.warning(f"Reset password decryption error: {e}")
        return hutao_response(
            1,
            f"解密修改密码数据失败: {str(e)}",
            status_code=400,
        )

    user = get_user_by_email(decrypted_email)
    if not user:
        return hutao_response(
            3,
            "用户不存在\nUser not found",
            status_code=404,
        )

    if not verify_code(decrypted_email, decrypted_code, request_type=RESET_PASSWORD_REQUEST_TYPE):
        return hutao_response(
            2,
            "验证码无效或已过期\nInvalid or expired verification code",
        )

    updated_user = update_user_password(decrypted_email, decrypted_password)
    if not updated_user:
        return hutao_response(
            4,
            "修改密码失败\nFailed to update password",
            status_code=500,
        )

    delete_verification_codes([decrypted_email], request_types=[RESET_PASSWORD_REQUEST_TYPE])
    logger.info(f"User password updated: {decrypted_email}")
    return hutao_response(
        0,
        "success",
        data=build_token_set(str(updated_user['_id'])),
    )


@auth_bp.route('/Passport/v2/Cancel', methods=['POST'])
def passport_cancel():
    """注销账号"""
    data = request.get_json(silent=True) or {}
    encrypted_email = data.get('UserName', '')
    encrypted_password = data.get('Password', '')
    encrypted_code = data.get('VerifyCode', '')
    access_token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()

    try:
        decrypted_email = decrypt_data(encrypted_email)
        decrypted_password = decrypt_data(encrypted_password)
        decrypted_code = decrypt_data(encrypted_code)
    except Exception as e:
        logger.warning(f"Cancel account decryption error: {e}")
        return hutao_response(
            1,
            f"解密注销账号数据失败: {str(e)}",
            status_code=400,
        )

    user = verify_user_credentials(decrypted_email, decrypted_password)
    if not user:
        return hutao_response(
            3,
            "邮箱或密码无效\nInvalid email or password",
        )

    if access_token:
        token_user_id = verify_token(access_token)
        if not token_user_id:
            return hutao_response(
                4,
                "访问令牌无效或已过期\nInvalid or expired access token",
                status_code=401,
            )
        if token_user_id != str(user['_id']):
            return hutao_response(
                5,
                "访问令牌与待注销账号不匹配\nAccess token does not match the target account",
                status_code=403,
            )

    if not verify_code(decrypted_email, decrypted_code, request_type=CANCEL_REGISTRATION_REQUEST_TYPE):
        return hutao_response(
            2,
            "验证码无效或已过期\nInvalid or expired verification code",
        )

    deleted_user = delete_user_account(decrypted_email)
    if not deleted_user:
        return hutao_response(
            6,
            "注销账号失败\nFailed to cancel account",
            status_code=500,
        )

    logger.info(f"User account cancelled: {decrypted_email}")
    return hutao_response(0, "success")


@auth_bp.route('/Passport/v2/UserInfo', methods=['GET'])
def passport_userinfo():
    """获取用户信息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    
    if not user_id:
        logger.warning("Invalid or expired token")
        return jsonify({
            "retcode": 1,
            "message": "登录云服务失败，token无效或已过期\nLogin failed, invalid or expired token",
            "data": None
        }), 401
    
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"User not found: {user_id}")
        return jsonify({
            "retcode": 2,
            "message": "用户不存在\nUser not found",
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
            "message": "刷新云服务token失败，刷新token无效或已过期，请重新登录云服务\nLogin failed, invalid or expired refresh token",
            "data": None
        })
    
    access_token = create_token(user_id)
    refresh_token = create_refresh_token(user_id)
    logger.info(f"Token refreshed for user_id: {user_id}")
    
    return jsonify({
        "retcode": 0,
        "message": "success",
        "data": {
            "AccessToken": access_token,
            "RefreshToken": refresh_token,
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

@auth_bp.route('/Passport/v2/RevokeAllTokens', methods=['POST'])
def passport_revoke_all_token():
    """注销Token"""
    logger.info("Token revoked")
    return jsonify({
        "retcode": 0,
        "message": "Token revoked successfully",
        "data": None
    })