"""
基于Redis的任务管理器
"""
import json
import time
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from redis import Redis
from loguru import logger
from config.workflows import WORKFLOW_TEMPLATES
from config.environments import environment_manager


class RedisTaskManager:
    """基于Redis的分布式任务管理器"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.lock_timeout = 300  # 任务锁超时时间（秒）
        logger.info("🚀 Redis任务管理器初始化完成")

    def create_task(self, workflow_name: str = None, environment: str = None,
                    task_data: Dict[str, Any] = None, source_channel: str = None,
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # 确定任务的工作流名称和目标环境
        if workflow_name:
            # 检查是否是换脸工作流
            if workflow_name == "face_swap" or workflow_name == "faceswap":
                # 换脸任务处理
                environment_name = environment or "face_swap"
                target_port = 8000  # 换脸服务端口

                # 支持通过 params 或 task_data 传递参数
                if params and "input_data" in params:
                    task_data = params["input_data"]

                # 验证换脸任务数据
                if not task_data:
                    raise ValueError(
                        "Face swap tasks require task_data or params with input_data")

                required_fields = ["source_url", "target_url"]
                missing_fields = [field for field in required_fields
                                  if field not in task_data]
                if missing_fields:
                    raise ValueError(
                        f"Missing required fields: {missing_fields}")

                # 使用与ComfyUI相同的params.input_data.wf_json格式
                task = {
                    "taskId": task_id,
                    "workflow": workflow_name,  # 使用一致的键名
                    "workflow_name": workflow_name,  # 保持向后兼容
                    "environment": environment_name,
                    "target_port": target_port,
                    "params": {
                        "input_data": {
                            "wf_json": task_data  # 统一使用params.input_data.wf_json
                        }
                    },
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "status": "PENDING",
                    "source_channel": source_channel  # 添加源渠道信息
                }

                # 保存到Redis
                self._save_task_to_redis(task)
                return task
            else:
                # 验证ComfyUI工作流是否存在
                available_workflows = environment_manager.get_all_workflows()
                if workflow_name not in available_workflows:
                    raise ValueError(
                        f"未知的工作流: {workflow_name}. 可用工作流: {available_workflows}")
        else:
            # 如果没有指定工作流，随机选择一个可用的工作流
            available_workflows = environment_manager.get_all_workflows()
            workflow_name = random.choice(
                available_workflows) if available_workflows else "basic_generation"

        # ComfyUI任务处理
        # 使用默认工作流模板
        workflow = WORKFLOW_TEMPLATES["default"].copy()

        # 随机修改参数
        if "3" in workflow and workflow["3"]["class_type"] == "KSampler":
            workflow["3"]["inputs"]["seed"] = random.randint(1, 1000000)

        if "6" in workflow and workflow["6"]["class_type"] == "CLIPTextEncode":
            prompts = [
                "a beautiful landscape with mountains and rivers",
                "a cute cat sitting on a wooden table",
                "abstract art with vibrant colors and shapes",
                "a peaceful garden with blooming flowers",
                "a modern city skyline at golden hour"
            ]
            workflow["6"]["inputs"]["text"] = random.choice(prompts)

        # 获取工作流对应的环境信息
        env_config = environment_manager.get_environment_by_workflow(
            workflow_name)
        environment_name = environment or (
            env_config.name if env_config else "comm")
        target_port = env_config.port if env_config else 3001

        task = {
            "taskId": task_id,
            "workflow": workflow_name,  # 使用一致的键名
            "workflow_name": workflow_name,  # 保持向后兼容
            "environment": environment_name,
            "target_port": target_port,
            "params": {
                "input_data": {
                    "wf_json": workflow
                }
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "PENDING",
            "source_channel": source_channel  # 添加源渠道信息
        }

        # 保存到Redis
        self._save_task_to_redis(task)
        return task

    def _save_task_to_redis(self, task: Dict[str, Any]):
        """保存任务到Redis"""
        task_id = task["taskId"]
        workflow_name = task.get("workflow") or task.get("workflow_name", "default")

        # 使用Redis Pipeline提高性能
        pipe = self.redis.pipeline()

        # 1. 保存任务详情到Hash
        task_key = f"task:{task_id}"
        pipe.hset(task_key, mapping={
            "taskId": task_id,
            "workflow": workflow_name,
            "workflow_name": workflow_name,
            "environment": task.get("environment", ""),
            "target_port": str(task.get("target_port", "")),
            "status": "PENDING",
            "params": json.dumps(task.get("params", {})),
            "created_at": task.get("created_at", ""),
            "updated_at": task.get("updated_at", ""),
            "source_channel": task.get("source_channel", "")
        })

        # 2. 添加到待处理队列
        pipe.rpush("queue:pending", task_id)

        # 如果有特定工作流，也加到工作流队列
        if workflow_name:
            pipe.rpush(f"queue:pending:{workflow_name}", task_id)

        # 3. 添加到状态索引
        pipe.sadd("tasks:status:PENDING", task_id)

        # 4. 添加到时间轴
        timestamp = time.time()
        pipe.zadd("tasks:timeline", {task_id: timestamp})

        # 5. 更新统计
        pipe.hincrby("stats:global", "total_created", 1)
        if workflow_name:
            pipe.hincrby(f"stats:workflow:{workflow_name}", "created", 1)

        # 执行所有操作
        pipe.execute()

        logger.info(f"✅ 任务创建成功: {task_id}, 工作流: {workflow_name}")

    def get_next_task(self, workflow_names: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """获取下一个待处理任务（带分布式锁）

        Args:
            workflow_names: 可选的工作流名称列表，用于筛选任务
        """

        # 确定要查询的队列
        queues = []
        if workflow_names:
            # 如果指定了工作流筛选，查找匹配的队列
            for wf in workflow_names:
                queues.append(f"queue:pending:{wf}")
            # 也检查通用队列
            queues.append("queue:pending")
        else:
            # 没有指定筛选，使用通用队列
            queues = ["queue:pending"]

        # 轮询所有队列
        for queue_key in queues:
            # 检查队列是否存在
            if not self.redis.exists(queue_key):
                continue

            # 从队列左侧弹出任务ID（FIFO）
            task_id = self.redis.lpop(queue_key)

            if not task_id:
                continue

            task_id = task_id.decode() if isinstance(task_id, bytes) else task_id

            # 尝试获取任务锁
            lock_key = f"lock:task:{task_id}"
            lock = self.redis.set(lock_key, "locked", nx=True, ex=self.lock_timeout)

            if not lock:
                logger.warning(f"⚠️  任务 {task_id} 已被其他consumer锁定，跳过")
                continue

            # 获取任务详情
            task = self._get_task_by_id(task_id)

            if task:
                # 如果指定了工作流筛选，验证任务工作流
                if workflow_names:
                    task_workflow = task.get("workflow_name") or task.get("workflow", "")
                    if task_workflow not in workflow_names:
                        # 任务不匹配，放回队列并释放锁
                        logger.debug(f"任务 {task_id} 工作流不匹配，放回队列")
                        self.redis.rpush(queue_key, task_id)
                        self.redis.delete(lock_key)
                        continue

                # 更新任务状态为FETCHED
                self._update_task_status_internal(
                    task_id,
                    "FETCHED",
                    old_status="PENDING"
                )

                logger.info(f"✅ 成功获取任务: {task_id}")
                return task

        # 没有找到匹配的任务
        # 如果队列很小，尝试创建新任务
        if workflow_names and len(workflow_names) > 0:
            queue_size = self.redis.llen("queue:pending")
            if queue_size < 5:
                try:
                    workflow_name = random.choice(workflow_names)
                    new_task = self.create_task(workflow_name=workflow_name)
                    new_task["status"] = "FETCHED"
                    # 更新状态为FETCHED
                    self._update_task_status_internal(
                        new_task["taskId"],
                        "FETCHED",
                        old_status="PENDING"
                    )
                    # 获取锁
                    lock_key = f"lock:task:{new_task['taskId']}"
                    self.redis.set(lock_key, "locked", nx=True, ex=self.lock_timeout)
                    return new_task
                except Exception as e:
                    logger.debug(f"创建新任务失败: {e}")

        return None

    def update_task_status(self, task_id: str, status: str,
                           message: str = None, started_at: str = None,
                           finished_at: str = None, output_data: Dict = None) -> bool:
        """更新任务状态"""
        return self._update_task_status_internal(
            task_id, status, message=message, started_at=started_at,
            finished_at=finished_at, output_data=output_data
        )

    def _update_task_status_internal(self, task_id: str, status: str,
                                     old_status: str = None, message: str = None,
                                     started_at: str = None, finished_at: str = None,
                                     output_data: Dict = None) -> bool:
        """内部状态更新方法"""
        task_key = f"task:{task_id}"

        # 检查任务是否存在
        if not self.redis.exists(task_key):
            logger.error(f"❌ 任务不存在: {task_id}")
            return False

        # 获取旧状态（如果未提供）
        if not old_status:
            old_status = self.redis.hget(task_key, "status")
            if old_status:
                old_status = old_status.decode() if isinstance(old_status, bytes) else old_status

        now = datetime.now().isoformat()

        # 使用Pipeline批量更新
        pipe = self.redis.pipeline()

        # 1. 更新任务Hash
        updates = {
            "status": status,
            "updated_at": now
        }

        if message:
            updates["task_message"] = message
        if started_at:
            updates["started_at"] = started_at if isinstance(started_at, str) else started_at.isoformat()
        if finished_at:
            updates["finished_at"] = finished_at if isinstance(finished_at, str) else finished_at.isoformat()
        if output_data:
            updates["output_data"] = json.dumps(output_data)

        pipe.hset(task_key, mapping=updates)

        # 2. 更新状态索引
        if old_status and old_status != status:
            pipe.srem(f"tasks:status:{old_status}", task_id)
        pipe.sadd(f"tasks:status:{status}", task_id)

        # 3. 如果是完成状态，添加到完成时间轴
        if status in ["COMPLETED", "FAILED"]:
            timestamp = time.time()
            pipe.zadd(f"tasks:timeline:{status.lower()}", {task_id: timestamp})

            # 更新统计
            pipe.hincrby("stats:global", f"total_{status.lower()}", 1)

            # 获取workflow并更新统计
            workflow = self.redis.hget(task_key, "workflow")
            if workflow:
                workflow = workflow.decode() if isinstance(workflow, bytes) else workflow
                pipe.hincrby(f"stats:workflow:{workflow}", status.lower(), 1)

            # 释放任务锁
            pipe.delete(f"lock:task:{task_id}")

        # 执行所有操作
        pipe.execute()

        logger.debug(f"✅ 任务状态更新: {task_id} {old_status} → {status}")
        return True

    def _get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取任务详情"""
        task_key = f"task:{task_id}"
        task_data = self.redis.hgetall(task_key)

        if not task_data:
            return None

        # 转换bytes到字符串
        task = {}
        for k, v in task_data.items():
            key = k.decode() if isinstance(k, bytes) else k
            value = v.decode() if isinstance(v, bytes) else v

            # 解析JSON字段
            if key in ["params", "output_data"] and value:
                try:
                    task[key] = json.loads(value)
                except:
                    task[key] = value
            else:
                task[key] = value

        # 确保向后兼容
        if "workflow" in task and "workflow_name" not in task:
            task["workflow_name"] = task["workflow"]

        return task

    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务（分页支持）"""
        # 获取所有任务ID（从时间轴）
        task_ids = self.redis.zrevrange("tasks:timeline", 0, 99)  # 最新100个

        tasks = []
        for task_id in task_ids:
            task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
            task = self._get_task_by_id(task_id)
            if task:
                tasks.append(task)

        # 获取队列长度
        queue_length = self.redis.llen("queue:pending")

        return {
            "tasks": tasks,
            "queue_length": queue_length
        }

    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = self.redis.hgetall("stats:global")

        # 转换bytes
        result = {}
        for k, v in stats.items():
            key = k.decode() if isinstance(k, bytes) else k
            try:
                value = int(v.decode() if isinstance(v, bytes) else v)
            except:
                value = 0
            result[key] = value

        # 添加实时状态统计
        result["pending"] = self.redis.scard("tasks:status:PENDING")
        result["fetched"] = self.redis.scard("tasks:status:FETCHED")
        result["processing"] = self.redis.scard("tasks:status:PROCESSING")
        result["completed"] = self.redis.scard("tasks:status:COMPLETED")
        result["failed"] = self.redis.scard("tasks:status:FAILED")

        return result

    def clear_all_tasks(self):
        """清空所有任务（危险操作，仅用于开发/测试）"""
        # 获取所有任务键
        task_keys = self.redis.keys("task:*")
        queue_keys = self.redis.keys("queue:*")
        stats_keys = self.redis.keys("stats:*")
        status_keys = self.redis.keys("tasks:status:*")
        timeline_keys = self.redis.keys("tasks:timeline*")
        lock_keys = self.redis.keys("lock:task:*")

        all_keys = task_keys + queue_keys + stats_keys + status_keys + timeline_keys + lock_keys

        if all_keys:
            self.redis.delete(*all_keys)

        logger.warning("⚠️  所有任务数据已清空")
