"""
应用配置设置
"""
import os
from typing import Optional

def get_env_bool(key: str, default: bool = False) -> bool:
    """获取布尔类型环境变量"""
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')

def get_env_int(key: str, default: int) -> int:
    """获取整数类型环境变量"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

# 应用环境
APP_ENV = os.getenv('APP_ENV', 'dev')

# 服务器配置
DEFAULT_HOST = os.getenv('HOST', '127.0.0.1')
DEFAULT_PORT = get_env_int('PORT', 8001)

# 任务API配置
task_api_url = os.getenv('TASK_API_URL', f'http://{DEFAULT_HOST}:{DEFAULT_PORT}/api')
api_key = os.getenv('API_KEY', '')
consumer_timeout = get_env_int('CONSUMER_TIMEOUT', 30)

# ComfyUI配置
comfyui_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:3001')

# 存储配置
storage_provider = os.getenv('STORAGE_PROVIDER', 'gcs')  # 'gcs' 或 'r2'

# Google Cloud Storage 配置
bucket_name = os.getenv('GCS_BUCKET_NAME', 'cdn-test-ai-undress-ai')
bucket_region = os.getenv('GCS_BUCKET_REGION', 'us-east-1')

# Cloudflare R2 配置
r2_bucket_name = os.getenv('R2_BUCKET_NAME', '')
r2_account_id = os.getenv('R2_ACCOUNT_ID', '')
r2_access_key = os.getenv('R2_ACCESS_KEY', '')
r2_secret_key = os.getenv('R2_SECRET_KEY', '')
r2_public_domain = os.getenv('R2_PUBLIC_DOMAIN', '')

# API签名配置
API_SECRET_KEY = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
API_SOURCE = "service"

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

# 服务器配置
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8001
