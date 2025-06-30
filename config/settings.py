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
comfyui_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:3002')

# 存储配置
storage_provider = os.getenv('STORAGE_PROVIDER', 'gcs')  # 'gcs' 或 'r2'

# Google Cloud Storage 配置
bucket_name = os.getenv('GCS_BUCKET_NAME', 'cdn-test-ai-undress-ai')
bucket_region = os.getenv('GCS_BUCKET_REGION', 'us-east-1')
cdn_url = os.getenv('CDN_URL', 'https://cdn.ai-undress.ai')

# Cloudflare R2 配置
r2_bucket_name = os.getenv('R2_BUCKET_NAME', '')
r2_account_id = os.getenv('R2_ACCOUNT_ID', '')
r2_access_key = os.getenv('R2_ACCESS_KEY', '')
r2_secret_key = os.getenv('R2_SECRET_KEY', '')
r2_public_domain = os.getenv('R2_PUBLIC_DOMAIN', '')

# Cloudflare Images 配置
cf_images_account_id = os.getenv('CF_IMAGES_ACCOUNT_ID', '')
cf_images_api_token = os.getenv('CF_IMAGES_API_TOKEN', '')
cf_images_delivery_domain = os.getenv('CF_IMAGES_DELIVERY_DOMAIN', '')  # 可选的自定义域名

# API签名配置
API_SECRET_KEY = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
API_SOURCE = "service"

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

# ComfyUI 就绪检查配置
COMFYUI_READY_TIMEOUT = get_env_int('COMFYUI_READY_TIMEOUT', 1000)  # 最长等待 10 分钟
COMFYUI_READY_INTERVAL = get_env_int('COMFYUI_READY_INTERVAL', 5)  # 每 5 秒检查一次
COMFYUI_READY_RETRIES = get_env_int('COMFYUI_READY_RETRIES', 200)  # 最多重试 60 次

# 服务器配置
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8001
