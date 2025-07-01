"""
任务消费者
"""
import asyncio
import aiohttp
from datetime import datetime, timezone
from loguru import logger
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
        
        logger.info(f"Task consumer {self.name} initialized.")
        logger.info(f"API URL: {self.api_url}")

    async def fetch_task(self, max_retries: int = 3):
        """从任务API获取一个待处理任务"""
        for attempt in range(max_retries):
            try:
                url = f"{self.api_url}/comfyui-fetch-task"
                logger.debug(f"Fetching task from: {url} (attempt {attempt + 1})")

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if not response.ok:
                            if attempt < max_retries - 1:
                                logger.warning(f"API request failed: {response.status}, retrying...")
                                await asyncio.sleep(2 ** attempt)  # 指数退避
                                continue
                            else:
                                logger.error(f"API request failed after {max_retries} attempts: {response.status}")
                                return None

                        response_data = await response.json()

                        if not isinstance(response_data, dict):
                            logger.error(f"API返回了非字典类型的数据: {type(response_data)}")
                            return None

                        task_id = response_data.get("taskId")
                        if task_id:
                            logger.info(f"Got task: {task_id}")
                            return response_data
                        else:
                            logger.debug("No task available")
                            return None

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error: {e}, retrying...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error fetching task: {e}")
                return None

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
