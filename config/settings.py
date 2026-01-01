"""
应用配置设置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录（config 目录的父目录）
_PROJECT_ROOT = Path(__file__).parent.parent

# 加载 .env 文件（优先 .env.prod，然后 .env）
# 使用绝对路径确保在任何工作目录下都能找到
APP_ENV ="prod"
_env_prod = _PROJECT_ROOT / '.env.prod'
_env_file = _PROJECT_ROOT / '.env.test'

if APP_ENV == 'prod':
    load_dotenv(_env_prod)
elif APP_ENV == 'test':
    load_dotenv(_env_file)

# 服务器配置（优先环境变量）
DEFAULT_HOST = os.getenv('HOST', '127.0.0.1')
DEFAULT_PORT = int(os.getenv('PORT', 8001))

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

# 根据环境硬编码配置
# if APP_ENV == 'local':
#     # 本地开发环境
#     TASK_API_URL = 'https://exactly-comic-lioness.ngrok-free.app'
#     COMFYUI_URL = 'http://127.0.0.1:3001'
# elif APP_ENV == 'test':
#     # 测试环境
#     TASK_API_URL = 'https://test-api.example.com/api'
#     COMFYUI_URL = 'http://127.0.0.1:3001'
# elif APP_ENV == 'prod':
#     # 生产环境
#     TASK_API_URL = 'https://api.example.com/api'
#     COMFYUI_URL = 'http://127.0.0.1:3001'
# else:
#     # 默认回退
#     TASK_API_URL = f'http://{DEFAULT_HOST}:{DEFAULT_PORT}/api'
#     COMFYUI_URL = 'http://127.0.0.1:3001'

# 向后兼容（废弃，请使用大写变量）
task_api_url = os.getenv('TASK_API_URL', '')
api_key = os.getenv('API_KEY', '')
consumer_timeout = get_env_int('CONSUMER_TIMEOUT', 30)

COMFYUI_URL = os.getenv('COMFYUI_URL', 'http://127.0.0.1:3001')
# 向后兼容（废弃，请使用 COMFYUI_URL）
comfyui_url =COMFYUI_URL

# 存储配置
storage_provider = os.getenv('STORAGE_PROVIDER', 'gcs')  # 'gcs' 或 'r2'

# Google Cloud Storage 配置
bucket_name = os.getenv('GCS_BUCKET_NAME', 'cdn-test-ai-undress-ai')
bucket_region = os.getenv('GCS_BUCKET_REGION', 'us-east-1')
cdn_url = os.getenv('CDN_URL', 'https://cdn.ai-undress.ai')

# Cloudflare R2 配置（与 aaaa 项目保持一致）
r2_bucket_name = os.getenv('R2_BUCKET', '')
r2_account_id = os.getenv('R2_ACCOUNT_ID', '')
r2_access_key = os.getenv('R2_ACCESS_KEY_ID', '')
r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY', '')
r2_public_domain = os.getenv('R2_PUBLIC_URL', 'https://static.z-image.vip')

# Cloudflare Images 配置
cf_images_account_id = os.getenv('CF_IMAGES_ACCOUNT_ID', '')
cf_images_api_token = os.getenv('CF_IMAGES_API_TOKEN', '')
cf_images_delivery_domain = os.getenv('CF_IMAGES_DELIVERY_DOMAIN', '')  # 可选的自定义域名

# API签名配置
API_SECRET_KEY = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
API_SOURCE = "service"

# 日志配置
LOG_LEVEL ="DEBUG"
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

# ComfyUI 就绪检查配置
COMFYUI_READY_TIMEOUT = get_env_int('COMFYUI_READY_TIMEOUT', 1000)  # 最长等待 10 分钟
COMFYUI_READY_INTERVAL = get_env_int('COMFYUI_READY_INTERVAL', 5)  # 每 5 秒检查一次
COMFYUI_READY_RETRIES = get_env_int('COMFYUI_READY_RETRIES', 200)  # 最多重试 60 次

# 结果节点类型配置
RESULT_NODE_TYPES = os.getenv('RESULT_NODE_TYPES', 'SaveImage,PreviewImage,SaveAudio').split(',')
RESULT_NODE_TYPES = [node_type.strip() for node_type in RESULT_NODE_TYPES if node_type.strip()]

# Face Swap Service 配置
FACE_SWAP_API_URL = os.getenv('FACE_SWAP_API_URL', 'http://localhost:8000')
FACE_SWAP_TIMEOUT = get_env_int('FACE_SWAP_TIMEOUT', 300)  # 5 minutes
FACE_SWAP_RETRY_COUNT = get_env_int('FACE_SWAP_RETRY_COUNT', 3)
FACEFUSION_ROOT = os.getenv('FACEFUSION_ROOT', '/Users/hzy/Code/zhuilai/video-faceswap')

# 工作流权限配置
# 允许的工作流列表（逗号分隔，支持通配符 *）
# 示例: "comfyui_*,basic_generation" 或 "*" 表示允许所有
# 留空或设为 "*" 表示允许所有工作流
ALLOWED_WORKFLOWS = "video-wan2-2-14b-i2v"
# ALLOWED_WORKFLOWS = "*"

# 是否记录被过滤的任务（用于调试）
LOG_FILTERED_TASKS = get_env_bool('LOG_FILTERED_TASKS', True)

# Redis配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = get_env_int('REDIS_PORT', 6379)
REDIS_DB = get_env_int('REDIS_DB', 0)
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_MAX_CONNECTIONS = get_env_int('REDIS_MAX_CONNECTIONS', 50)

# Upstash Redis REST API 配置（远程Redis）
UPSTASH_REDIS_REST_URL="https://saved-jackal-19117.upstash.io"
UPSTASH_REDIS_REST_TOKEN="AUqtAAIncDI1Y2Y3NWRhNzZhZjg0MTQyODY1YzBiYjIyMDNmYTE1N3AyMTkxMTc"

# 任务管理器类型: 'memory' 或 'redis'
TASK_MANAGER_TYPE = "redis"

# 消费者模式: 'redis_queue' (Redis三级优先队列) 或 'http' (HTTP轮询)
CONSUMER_MODE = os.getenv('CONSUMER_MODE', 'redis_queue')

# 任务结果回调配置
TASK_CALLBACK_URL = os.getenv('TASK_CALLBACK_URL', '')  # 任务完成后的回调地址
TASK_CALLBACK_TIMEOUT = get_env_int('TASK_CALLBACK_TIMEOUT', 30)  # 回调超时时间（秒）
