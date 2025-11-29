"""
任务消费者
支持双模式：HTTP 轮询 / Redis 队列
"""
import asyncio
from utils import get_task_api_urls
import httpx
from loguru import logger
from consumer.processor_registry import processor_registry
from httpx_retries import RetryTransport, Retry
from utils.workflow_filter import workflow_filter
from config.settings import CONSUMER_MODE
from consumer.queue_consumer import get_queue_consumer
from consumer.task_schema import normalize_queue_task
from consumer.result_callback import get_result_callback


class TaskConsumer:
    """任务消费者 - 支持 HTTP 轮询和 Redis 队列两种模式"""

    def __init__(self, name: str):
        self.name = name
        self.api_urls = get_task_api_urls()  # 获取多个API URL
        self.running = False
        self.processor_registry = processor_registry
        self.source_stats = {}
        self.consumer_mode = CONSUMER_MODE  # 'http' 或 'redis_queue'
        self.queue_consumer = get_queue_consumer() if self.consumer_mode == 'redis_queue' else None
        self.result_callback = get_result_callback()

        # 使用 httpx-retries 包的配置
        retry = Retry(total=3, backoff_factor=0.5)
        self.retry_transport = RetryTransport(retry=retry)

        logger.info(f"统一任务消费者 {self.name} 初始化完成")
        logger.info(f"消费模式: {self.consumer_mode}")
        if self.consumer_mode == 'http':
            logger.info(f"API URLs: {self.api_urls}")
        elif self.consumer_mode == 'redis_queue':
            if self.queue_consumer and self.queue_consumer.is_available():
                logger.info("Redis 队列模式已就绪")
            else:
                logger.warning("Redis 队列不可用，将回退到 HTTP 模式")
                self.consumer_mode = 'http'
        logger.info(
            f"支持的处理器: {list(self.processor_registry.list_processors().keys())}")

    async def fetch_task(self):
        """从任务源获取一个待处理任务"""
        # Redis 队列模式
        if self.consumer_mode == 'redis_queue' and self.queue_consumer:
            return await self._fetch_from_redis_queue()

        # HTTP 轮询模式（默认）
        return await self._fetch_from_http()

    async def _fetch_from_redis_queue(self):
        """从 Redis 三级优先队列获取任务"""
        try:
            raw_task = await self.queue_consumer.fetch_task()
            if raw_task:
                # 标准化任务格式
                task = normalize_queue_task(raw_task)
                task["source_channel"] = "redis_queue"
                logger.info(f"从 Redis 队列获取任务: {task.get('taskId')}")
                return task
            return None
        except Exception as e:
            logger.error(f"从 Redis 队列获取任务失败: {e}")
            return None

    async def _fetch_from_http(self):
        """从 HTTP API 轮询获取任务"""
        # 轮询所有配置的API源
        for api_url in self.api_urls:
            url = f"{api_url}/api/comm/task/fetch"
            logger.debug(f"Fetching task from: {url}")

            task = await self._try_fetch_from_url(url)
            if task:
                logger.info(
                    f"Successfully got task {task.get('taskId')} from: {api_url}")
                return task
            else:
                logger.debug(f"No task available from: {api_url}")

        # 所有源都没有任务
        logger.debug("No tasks available from any configured source")
        return None

    async def _try_fetch_from_url(self, url: str):
        """尝试从单个URL获取任务"""
        # 获取API基础URL（移除路径部分）
        api_base_url = url.split('/api/comm/task/fetch')[0]

        try:
            # 构建请求参数，添加工作流筛选
            params = {}
            allowed_workflows = workflow_filter.get_allowed_workflows()

            # 如果有特定的允许工作流（不是允许所有），则添加筛选参数
            if allowed_workflows and '*' not in allowed_workflows:
                params['workflowNames'] = allowed_workflows
                logger.debug(f"请求任务时添加工作流筛选: {allowed_workflows}")

            async with httpx.AsyncClient(
                timeout=10.0,
                transport=self.retry_transport
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                response_data = response.json()

                if not isinstance(response_data, dict):
                    logger.debug(
                        f"API返回了非字典类型的数据: {type(response_data)} from {api_base_url}")
                    return None

                # 处理新的 API 响应格式
                code = response_data.get("code")
                message = response_data.get("message", "")
                data = response_data.get("data")
                success = response_data.get("success", code == 200)

                if not success:
                    logger.debug(
                        f"API请求失败: code={code}, message={message} from {api_base_url}")
                    return None

                # 从 data 字段中获取任务信息
                if not data:
                    logger.debug(
                        f"No task available (data is empty) from {api_base_url}")
                    return None

                task_id = data.get("taskId")
                if task_id:
                    logger.debug(f"Got task: {task_id} from {api_base_url}")
                    # 为任务添加源渠道信息
                    data["source_channel"] = api_base_url
                    logger.debug(
                        f"Task {task_id} marked with source_channel: {api_base_url}")
                    return data
                else:
                    logger.debug(f"No task available from {api_base_url}")
                    return None

        except httpx.HTTPError as e:
            logger.debug(
                f"Network error fetching task from {api_base_url}: {e}")
            return None
        except Exception as e:
            logger.debug(
                f"Unexpected error fetching task from {api_base_url}: {e}")
            return None

    async def process_task(self, task):
        """处理单个任务"""
        task_id = task.get("taskId")
        # 兼容两种字段名: workflow_name 和 workflow
        workflow_name = task.get("workflow_name") or task.get("workflow", "")
        callback_url = task.get("callbackUrl") or task.get("callback_url")

        if not task_id:
            logger.error("Task missing taskId")
            return None

        # 先检查工作流是否被允许
        if not workflow_filter.is_workflow_allowed(workflow_name):
            logger.info(f"跳过任务 {task_id} - 工作流 '{workflow_name}' 不被当前机器允许")
            # 返回 None，任务保持 PENDING 状态，让其他机器处理
            return None

        logger.info(f"开始处理任务: {task_id} (工作流: {workflow_name})")
        logger.debug(f"任务详情: {task}")

        # 检测测试任务：taskId 以 test_task_ 开头 或 workflowName 是 test_workflow
        is_test_task = (
            task_id.startswith("test_task_") or
            workflow_name == "test_workflow"
        )

        if is_test_task:
            logger.info(f"[TEST] 检测到测试任务 {task_id}，直接标记完成")
            # 构造测试结果
            test_result = {
                "status": "COMPLETED",
                "taskId": task_id,
                "message": "测试任务已完成（跳过实际处理）",
                "is_test": True
            }
            # 发送成功回调
            if self.consumer_mode == 'redis_queue':
                await self.result_callback.send_success(
                    task_id=task_id,
                    result=test_result
                )
            logger.info(f"[TEST] 测试任务 {task_id} 已标记完成")
            return test_result

        # Redis 队列模式下标记任务为处理中
        if self.consumer_mode == 'redis_queue':
            await self.result_callback.send_processing(task_id)

        try:
            # 根据工作流名称获取对应的处理器
            processor = self.processor_registry.get_processor(workflow_name)

            if not processor:
                # 这种情况理论上不应该发生，因为已经在上面检查过了
                logger.warning(f"工作流 '{workflow_name}' 被过滤或未找到处理器")
                return None

            processor_type = type(processor).__name__
            logger.info(f"使用处理器: {processor_type}")

            # 使用处理器处理任务 - 在线程池中运行同步代码
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, processor.process, task)

            if result:
                logger.info(f"任务 {task_id} 完成 (处理器: {processor_type})")
                logger.debug(f"任务结果: {result}")

                # Redis 队列模式下写入结果到 Redis
                if self.consumer_mode == 'redis_queue':
                    await self.result_callback.send_success(
                        task_id=task_id,
                        result=result
                    )
            else:
                logger.error(
                    f"任务 {task_id} 处理失败 - 返回结果为空 (处理器: {processor_type})")
                logger.error(f"任务详情: {task}")

                # Redis 队列模式下写入失败结果到 Redis
                if self.consumer_mode == 'redis_queue':
                    await self.result_callback.send_failure(
                        task_id=task_id,
                        error="处理器返回空结果"
                    )

            return result
        except Exception as e:
            logger.error(f"处理任务 {task_id} 时发生异常: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"任务详情: {task}")
            logger.debug(f"异常详情:", exc_info=True)

            # Redis 队列模式下写入异常结果到 Redis
            if self.consumer_mode == 'redis_queue':
                await self.result_callback.send_failure(
                    task_id=task_id,
                    error=str(e)
                )

            return None

    async def start(self):
        """启动消费者循环"""
        self.running = True
        logger.info(f"Consumer {self.name} 启动")

        while self.running:
            try:
                task = await self.fetch_task()
                if task:
                    await self.process_task(task)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(3)

    def stop(self):
        """停止消费者"""
        self.running = False
        logger.info(f"Consumer {self.name} 停止")


async def start_consumer():
    """启动consumer的函数，供main.py调用"""
    logger.info("统一任务消费者启动")
    logger.info("智能分发模式：支持 ComfyUI 和 FaceFusion 任务")

    # 显示当前机器的工作流过滤配置
    filter_stats = workflow_filter.get_filter_stats()
    logger.info("工作流过滤配置:")
    if filter_stats['allows_all']:
        logger.info("  - 允许的工作流: 所有")
    else:
        logger.info(
            f"  - 允许的工作流: {', '.join(filter_stats['allowed_workflows'])}")

    # 创建统一的consumer
    consumer = TaskConsumer("unified-consumer")

    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，系统正在关闭")
    finally:
        consumer.stop()
        logger.info("统一消费者已停止")
