"""
任务消费者
"""
import asyncio
from typing import Optional
from utils import get_task_api_urls
import httpx
from loguru import logger
from consumer.processor_registry import processor_registry
from httpx_retries import RetryTransport, Retry
from utils.workflow_filter import workflow_filter


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
        allowed_workflows = workflow_filter.get_allowed_workflows()

        # 确定要传递的工作流筛选参数
        workflow_names_param = None
        if allowed_workflows and '*' not in allowed_workflows:
            # 有特定的允许工作流列表，作为数组传递
            workflow_names_param = allowed_workflows
            logger.debug(f"🎯 使用工作流筛选: {workflow_names_param}")
        else:
            logger.debug("📋 不使用工作流筛选（允许所有）")

        # 轮询所有配置的API源
        for api_url in self.api_urls:
            url = f"{api_url}/api/comm/task/fetch"
            workflows_desc = ', '.join(workflow_names_param) if workflow_names_param else "any"
            logger.debug(f"Fetching task from: {url} (workflows: {workflows_desc})")

            task = await self._try_fetch_from_url(url, workflow_names_param)
            if task:
                logger.info(
                    f"✅ Successfully got task {task.get('taskId')} from: {api_url} (workflows: {workflows_desc})")
                return task
            else:
                logger.debug(f"No task available from: {api_url} (workflows: {workflows_desc})")

        # 所有源都没有任务
        logger.debug("No tasks available from any configured source")
        return None

    async def _try_fetch_from_url(self, url: str, workflow_names: Optional[list] = None):
        """尝试从单个URL获取任务

        Args:
            url: API端点URL
            workflow_names: 可选的工作流名称列表，用于筛选特定工作流的任务
        """
        # 获取API基础URL（移除路径部分）
        api_base_url = url.split('/api/comm/task/fetch')[0]

        try:
            # 构建请求参数
            params = {}
            if workflow_names:
                # FastAPI 的 Query(List[str]) 需要传递多个同名参数
                # httpx 会自动处理列表参数
                params['workflow_names'] = workflow_names

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
        workflow_name = task.get("workflow_name", "")

        if not task_id:
            logger.error("Task missing taskId")
            return None

        # 先检查工作流是否被允许
        if not workflow_filter.is_workflow_allowed(workflow_name):
            logger.info(f"⏭️  跳过任务 {task_id} - 工作流 '{workflow_name}' 不被当前机器允许")
            # 返回 None，任务保持 PENDING 状态，让其他机器处理
            return None

        logger.info(f"开始处理任务: {task_id} (工作流: {workflow_name})")
        logger.debug(f"任务详情: {task}")

        try:
            # 根据工作流名称获取对应的处理器
            processor = self.processor_registry.get_processor(workflow_name)

            if not processor:
                # 这种情况理论上不应该发生，因为已经在上面检查过了
                logger.warning(f"⚠️  工作流 '{workflow_name}' 被过滤或未找到处理器")
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

    # 显示当前机器的工作流过滤配置
    filter_stats = workflow_filter.get_filter_stats()
    logger.info("🔒 工作流过滤配置:")
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
        logger.info("🛑 收到中断信号，系统正在关闭")
    finally:
        consumer.stop()
        logger.info("✅ 统一消费者已停止")
