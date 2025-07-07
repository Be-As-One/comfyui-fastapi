"""
任务消费者
"""
import asyncio
import httpx
from datetime import datetime, timezone
from loguru import logger
from httpx_retry import RetryTransport
from config.settings import consumer_timeout, task_api_url, api_key
from consumer.processors.comfyui import ComfyUIProcessor
from services.comfyui_service import comfyui_service

class TaskConsumer:
    """任务消费者"""
    
    def __init__(self, name: str):
        self.name = name
        self.api_url = task_api_url
        self.running = False
        self.processor = ComfyUIProcessor()
        
        # 创建带重试功能的传输层
        self.retry_transport = RetryTransport(
            wrapped_transport=httpx.AsyncHTTPTransport(),
            max_attempts=3,  # 总共3次尝试
            backoff_factor=2.0,  # 指数退避因子
            status_codes={408, 429, 500, 502, 503, 504}  # 需要重试的状态码
        )
        
        logger.info(f"Task consumer {self.name} initialized.")
        logger.info(f"API URL: {self.api_url}")

    async def fetch_task(self):
        """从任务API获取一个待处理任务"""
        url = f"{self.api_url}/api/comm/task/fetch"
        logger.debug(f"Fetching task from: {url}")
        
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                transport=self.retry_transport
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                response_data = await response.json()
                
                if not isinstance(response_data, dict):
                    logger.error(f"API返回了非字典类型的数据: {type(response_data)}")
                    return None
                
                # 处理新的 API 响应格式
                code = response_data.get("code")
                message = response_data.get("message", "")
                data = response_data.get("data")
                success = response_data.get("success", code == 200)
                
                if not success:
                    logger.error(f"API请求失败: code={code}, message={message}")
                    return None
                
                # 从 data 字段中获取任务信息
                if not data:
                    logger.debug("No task available (data is empty)")
                    return None
                
                task_id = data.get("taskId")
                if task_id:
                    logger.info(f"Got task: {task_id}")
                    return data
                else:
                    logger.debug("No task available")
                    return None
                    
        except httpx.HTTPError as e:
            logger.error(f"Network error fetching task: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching task: {e}")
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
            # 使用处理器处理任务 - 在线程池中运行同步代码
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.processor.process, task)

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
