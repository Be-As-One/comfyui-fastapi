"""
Redis连接配置
"""
import os
from redis import Redis, ConnectionPool
from loguru import logger


class RedisConfig:
    """Redis配置管理"""

    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        self.db = int(os.getenv('REDIS_DB', '0'))
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))

        # 创建连接池
        self.pool = ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            max_connections=self.max_connections,
            decode_responses=False  # 我们手动处理解码
        )

    def get_client(self) -> Redis:
        """获取Redis客户端"""
        return Redis(connection_pool=self.pool)

    def health_check(self) -> bool:
        """健康检查"""
        try:
            client = self.get_client()
            client.ping()
            logger.info(f"✅ Redis连接成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            return False


# 全局Redis配置实例
redis_config = RedisConfig()


def get_redis_client() -> Redis:
    """获取Redis客户端（工厂函数）"""
    return redis_config.get_client()
