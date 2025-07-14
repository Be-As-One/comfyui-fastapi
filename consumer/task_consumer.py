"""
任务消费者
"""
import asyncio
import httpx
from loguru import logger
from httpx_retry import RetryTransport
from config.settings import get_task_api_urls
from consumer.processors.comfyui import ComfyUIProcessor
from consumer.processors.face_swap import face_swap_processor


class TaskConsumer:
    """任务消费者"""

    def __init__(self, name: str):
        self.name = name
        self.api_urls = get_task_api_urls()  # 获取多个API URL
        self.running = False
        self.comfyui_processor = ComfyUIProcessor()
        self.face_swap_processor = face_swap_processor

        # 创建带重试功能的传输层
        self.retry_transport = RetryTransport(
            wrapped_transport=httpx.AsyncHTTPTransport(),
            max_attempts=3,  # 总共3次尝试
            backoff_factor=2.0,  # 指数退避因子
            status_codes={408, 429, 500, 502, 503, 504}  # 需要重试的状态码
        )

        logger.info(f"Task consumer {self.name} initialized.")
        if len(self.api_urls) == 1:
            logger.info(f"Single task source configured: {self.api_urls[0]}")
        else:
            logger.info(f"Multi-source mode: {len(self.api_urls)} task sources configured:")
            for i, url in enumerate(self.api_urls, 1):
                logger.info(f"  Source {i}: {url}")

    async def fetch_task(self):
        """从多个任务源轮询获取一个待处理任务"""
        # 轮询所有配置的API源
        for api_url in self.api_urls:
            url = f"{api_url}/api/comm/task/fetch"
            logger.debug(f"Fetching task from: {url}")

            task = await self._try_fetch_from_url(url)
            if task:
                logger.info(f"Successfully got task {task.get('taskId')} from: {api_url}")
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

        # 更新统计信息
        if api_base_url in self.source_stats:
            self.source_stats[api_base_url]["attempts"] += 1

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                transport=self.retry_transport
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                response_data = await response.json()

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
        if not task_id:
            logger.error("Task missing taskId")
            return None

        logger.info(f"开始处理任务: {task_id}")
        logger.debug(f"任务详情: {task}")

        try:
            # Determine task type and use appropriate processor
            # Check both "workflow" and "workflow_name" keys for compatibility
            workflow_name = task.get("workflow") or task.get(
                "workflow_name", "default")

            if workflow_name == "face_swap":
                # Process face swap task asynchronously
                logger.info(f"Processing face swap task: {task_id}")
                # Extract input_data from params (unified format)
                params = task.get("params", {})
                input_data = params.get("input_data", {})
                if not input_data:
                    logger.error(
                        f"Face swap task {task_id} missing params.input_data")
                    return None
                result = await self.face_swap_processor.process_task(input_data)
            else:
                # Process ComfyUI task synchronously in thread pool
                logger.info(f"Processing ComfyUI task: {task_id}")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self.comfyui_processor.process, task
                )

            if result:
                logger.info(f"任务 {task_id} 完成")
                logger.debug(f"任务结果: {result}")
            else:
                logger.error(f"任务 {task_id} 处理失败 - 返回结果为空")
                logger.error(f"任务详情: {task}")

            return result
        except Exception as e:
            logger.error(f"处理任务 {task_id} 时发生异常: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"任务详情: {task}")
            logger.debug(f"异常详情:", exc_info=True)
            return None

    async def start(self):
        """启动消费者循环"""
        self.running = True
        logger.info(f"🚀 Consumer {self.name} 启动")

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
        logger.info(f"🛑 Consumer {self.name} 停止")

async def start_consumer():
    """启动consumer的函数，供main.py调用"""
    logger.info("🚀 ComfyUI Consumer 启动")
    logger.info("📋 多环境模式：将在任务执行时动态连接对应的 ComfyUI 服务")

    # 创建单个consumer
    consumer = TaskConsumer("main-consumer")

    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，系统正在关闭")
    finally:
        consumer.stop()
        logger.info("✅ Consumer已停止")
