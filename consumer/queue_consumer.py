"""
三级优先队列消费器
从 Upstash Redis 按优先级消费任务: vip > normal > guest
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List

from config.upstash_redis import get_upstash_client

logger = logging.getLogger(__name__)

# 三级优先队列名称（按优先级从高到低）
PRIORITY_QUEUES: List[str] = [
    "gpu:tasks:vip",      # 最高优先级 - 付费用户
    "gpu:tasks:normal",   # 中等优先级 - 普通登录用户
    "gpu:tasks:guest"     # 最低优先级 - 未登录用户
]


class QueueConsumer:
    """三级优先队列消费器"""

    def __init__(self, consumer_id: str = "queue-consumer"):
        self.consumer_id = consumer_id
        self.redis = get_upstash_client()
        self.running = False
        self._poll_interval = 1  # 轮询间隔（秒）

    def is_available(self) -> bool:
        """检查 Redis 连接是否可用"""
        if self.redis is None:
            return False
        try:
            self.redis.ping()
            return True
        except Exception:
            return False

    async def fetch_task(self) -> Optional[Dict[str, Any]]:
        """
        从三级优先队列获取任务
        按优先级顺序检查队列：vip > normal > guest

        Returns:
            任务数据字典，如果没有任务则返回 None
        """
        if not self.is_available():
            logger.warning(f"[{self.consumer_id}] Redis 不可用，跳过获取任务")
            return None

        try:
            # Upstash REST API 不支持 BRPOP，使用轮询方式
            # 按优先级顺序检查每个队列
            for queue_name in PRIORITY_QUEUES:
                task_json = self.redis.rpop(queue_name)
                if task_json:
                    task = json.loads(task_json) if isinstance(task_json, str) else task_json
                    logger.info(f"[{self.consumer_id}] 从 {queue_name} 获取任务: {task.get('taskId', 'unknown')}")
                    return task

            return None

        except json.JSONDecodeError as e:
            logger.error(f"[{self.consumer_id}] 任务 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"[{self.consumer_id}] 获取任务异常: {e}")
            return None

    async def get_queue_lengths(self) -> Dict[str, int]:
        """获取各队列长度"""
        if not self.is_available():
            return {}

        lengths = {}
        for queue_name in PRIORITY_QUEUES:
            try:
                lengths[queue_name] = self.redis.llen(queue_name) or 0
            except Exception:
                lengths[queue_name] = -1
        return lengths

    async def push_task(self, task: Dict[str, Any], priority: str = "normal") -> bool:
        """
        推送任务到指定优先级队列（用于测试）

        Args:
            task: 任务数据
            priority: 优先级 (vip/normal/guest)
        """
        if not self.is_available():
            return False

        queue_map = {
            "vip": "gpu:tasks:vip",
            "normal": "gpu:tasks:normal",
            "guest": "gpu:tasks:guest"
        }
        queue_name = queue_map.get(priority, "gpu:tasks:normal")

        try:
            task_json = json.dumps(task)
            self.redis.lpush(queue_name, task_json)
            logger.info(f"[{self.consumer_id}] 任务 {task.get('taskId')} 推送到 {queue_name}")
            return True
        except Exception as e:
            logger.error(f"[{self.consumer_id}] 推送任务失败: {e}")
            return False


# 全局消费器实例
_queue_consumer: Optional[QueueConsumer] = None


def get_queue_consumer() -> Optional[QueueConsumer]:
    """获取队列消费器单例"""
    global _queue_consumer
    if _queue_consumer is None:
        _queue_consumer = QueueConsumer()
    return _queue_consumer
