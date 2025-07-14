"""
任务消费者
"""
import asyncio
from utils import get_task_api_urls
import httpx
from loguru import logger
from consumer.processor_registry import processor_registry
from httpx_retries import RetryTransport, Retry


class TaskConsumer:
    """任务消费者"""

    def __init__(self, name: str):
        self.name = name
        self.api_urls = get_task_api_urls()  # 获取多个API URL
        self.running = False
        self.processor_registry = processor_registry
        self.source_stats = {}
        # 使用 httpx-retries 包的配置
        retry = Retry(total=3, backoff_factor=0.5)
        self.retry_transport = RetryTransport(retry=retry)
        logger.info(f"统一任务消费者 {self.name} 初始化完成")
        logger.info(f"API URLs: {self.api_urls}")
        logger.info(
            f"支持的处理器: {list(self.processor_registry.list_processors().keys())}")

    async def fetch_task(self):
        """从多个任务源轮询获取一个待处理任务"""
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
            async with httpx.AsyncClient(
                timeout=10.0,
                transport=self.retry_transport
            ) as client:
                response = await client.get(url)
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
        workflow_name = task.get("workflow_name", "")

        if not task_id:
            logger.error("Task missing taskId")
            return None

        logger.info(f"开始处理任务: {task_id} (工作流: {workflow_name})")
        logger.debug(f"任务详情: {task}")

        try:
            # 根据工作流名称获取对应的处理器
            processor = self.processor_registry.get_processor(workflow_name)

            if not processor:
                logger.error(f"❌ 未找到适合的处理器: {workflow_name}")
                return None

            processor_type = type(processor).__name__
            logger.info(f"🎯 使用处理器: {processor_type}")

            # 使用处理器处理任务 - 在线程池中运行同步代码
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, processor.process, task)

            if result:
                logger.info(f"✅ 任务 {task_id} 完成 (处理器: {processor_type})")
                logger.debug(f"任务结果: {result}")
            else:
                logger.error(
                    f"❌ 任务 {task_id} 处理失败 - 返回结果为空 (处理器: {processor_type})")
                logger.error(f"任务详情: {task}")

            return result
        except Exception as e:
            logger.error(f"❌ 处理任务 {task_id} 时发生异常: {str(e)}")
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
    logger.info("🚀 统一任务消费者启动")
    logger.info("🎯 智能分发模式：支持 ComfyUI 和 FaceFusion 任务")
    logger.info("📋 支持的工作流类型:")
    logger.info("  - faceswap → FaceFusion 处理器")
    logger.info("  - comfyui_* → ComfyUI 处理器")
    logger.info(
        "  - basic_generation/text_to_image/image_to_image → ComfyUI 处理器")

    # 创建统一的consumer
    consumer = TaskConsumer("unified-consumer")

    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，系统正在关闭")
    finally:
        consumer.stop()
        logger.info("✅ 统一消费者已停止")
