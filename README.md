# Snap.Server
Snap.Hutao新后端API

## 部署方法

> **资源和环境要求**  
> 服务器硬件：
> 最低1核CPU，1GB内存
>
> 运行环境：  
> `Windows10`及以上、`Windows Server 2019`及以上、`Linux`  
> `Python3.12`及以上  
> `MongoDB`

### 在服务器生成RSA密钥

执行以下代码在根目录生成密钥：
```python
from Crypto.PublicKey import RSA

# 生成 2048 位 RSA 密钥对
key = RSA.generate(2048)

private_key = key.export_key()
public_key = key.publickey().export_key()

with open("private.pem", "wb") as f:
    f.write(private_key)

with open("public.pem", "wb") as f:
    f.write(public_key)

print("Keys generated.")

```

**确保客户端的公钥和生成的相同，否则将无法使用账户功能**

### 创建配置文件

创建`config.json`文件，示例内容如下：

```json
{
  "SECRET_KEY": "jwt_secret_key",
  "MONGO_URI": "mongodb+srv://wdgwdg889_db_user:xxxxxx@cluster0.eplrcvl.mongodb.net/?appName=Cluster0",
  "TIMEZONE": "Asia/Shanghai",
  "ISTEST_MODE": false,
  "SERVER": {
    "HOST": "0.0.0.0",
    "PORT": 5222,
    "DEBUG": false
  },
  "JWT": {
    "ALGORITHM": "HS256",
    "EXPIRATION_HOURS": 24
  },
  "EMAIL": {
    "GMAIL_USER": "wdgwdg889@gmail.com",
    "APP_PASSWORD": "",
    "APP_NAME": "WDG Snap Hutao",
    "OFFICIAL_WEBSITE": "https://htserver.wdg.cloudns.ch/",
    "SUBJECT": "WDG Snap Hutao 验证码"
  },
  "RSA": {
    "PRIVATE_KEY_FILE": "private.pem",
    "PUBLIC_KEY_FILE": "public.pem"
  },
  "VERIFICATION_CODE": {
    "EXPIRE_MINUTES": 10
  },
  "LOGGING": {
    "LEVEL": "DEBUG",
    "FORMAT": ""
  }
}
```

参数说明：

| 参数 | 说明 |
|------|------|
| SECRET_KEY | 用于JWT签名的密钥，请设置为复杂字符串 |
| MONGO_URI | MongoDB连接字符串 |
| TIMEZONE | 服务器时区 |
| ISTEST_MODE | 是否启用测试模式,测试模式下部分功能将返回默认值，不连接数据库 |
| SERVER.HOST | 服务器监听地址 |
| SERVER.PORT | 服务器监听端口 |
| SERVER.DEBUG | 是否启用Flask的调试模式 |
| JWT.ALGORITHM | JWT签名算法 |
| JWT.EXPIRATION_HOURS | JWT过期时间（小时） |
| EMAIL.GMAIL_USER | 用于发送验证邮件的Gmail账号 |
| EMAIL.APP_PASSWORD | Gmail应用专用密码 |
| EMAIL.APP_NAME | 应用名称，用于邮件显示 |
| EMAIL.OFFICIAL_WEBSITE | 官方网站地址，用于邮件中的链接 |
| EMAIL.SUBJECT | 验证邮件的主题 |
| RSA.PRIVATE_KEY_FILE | RSA私钥文件路径 |
| RSA.PUBLIC_KEY_FILE | RSA公钥文件路径 |
| VERIFICATION_CODE.EXPIRE_MINUTES | 验证码过期时间（分钟） |
| LOGGING.LEVEL | 日志记录级别，生产环境建议设置为INFO |
| LOGGING.FORMAT | 日志记录格式 |

### 开发环境启动方法

确保已安装依赖：
```
pip install -r requirements.txt
```
运行Flask应用：
```
python app.py
```

### 生产环境启动方法

建议使用Gunicorn部署：
```
pip install -r requirements.txt && python -m gunicorn run:app --bind 0.0.0.0:5222 --workers 4 --threads 2 --access-logfile - --error-logfile -
```

请根据服务器性能调整`--workers`和`--threads`参数。

### API文档

API文档可以在该地址访问：

https://rdgm3wrj7r.apifox.cn/

### 注意事项

在轻量使用的场景下，可以直接使用MongoDB Atlas的免费套餐，但在高并发场景下，建议使用自建MongoDB服务器以获得更好的性能和稳定性。

新MongoDB数据库会在写入数据时自动创建，无需手动创建数据库和集合。
