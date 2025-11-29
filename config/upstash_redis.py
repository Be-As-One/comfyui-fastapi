"""
Upstash Redis 客户端配置
使用 REST API 连接远程 Upstash Redis
"""
import logging
from typing import Optional
from upstash_redis import Redis

from config.settings import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

logger = logging.getLogger(__name__)

# 全局客户端实例
_upstash_client: Optional[Redis] = None


def get_upstash_client() -> Optional[Redis]:
    """获取 Upstash Redis 客户端单例"""
    global _upstash_client

    if _upstash_client is not None:
        return _upstash_client

    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        logger.warning("⚠️ Upstash Redis 未配置: 缺少 UPSTASH_REDIS_REST_URL 或 UPSTASH_REDIS_REST_TOKEN")
        return None

    try:
        _upstash_client = Redis(
            url=UPSTASH_REDIS_REST_URL,
            token=UPSTASH_REDIS_REST_TOKEN
        )
        # 测试连接
        _upstash_client.ping()
        logger.info("✅ Upstash Redis 连接成功")
        return _upstash_client
    except Exception as e:
        logger.error(f"❌ Upstash Redis 连接失败: {e}")
        return None


def is_upstash_available() -> bool:
    """检查 Upstash Redis 是否可用"""
    client = get_upstash_client()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False
