#!/usr/bin/env python3
"""
ComfyUI 主入口

使用方法:
    python main.py                    # 启动API + Consumer
    python main.py api               # 只启动API
    python main.py consumer          # 只启动Consumer
"""

import os
import asyncio
import typer
import uvicorn
from loguru import logger
from consumer.task_consumer import start_consumer
from utils.logger import setup_logger
from config.settings import DEFAULT_HOST, DEFAULT_PORT

# 设置日志
setup_logger()

# 初始化存储管理器
def init_storage():
    """初始化存储管理器"""
    try:
        from core.storage import StorageManager, set_storage_manager
        logger.info("🔧 初始化存储管理器...")

        # 手动创建存储管理器实例
        storage_manager = StorageManager()
        storage_manager.initialize()

        # 设置为全局实例
        set_storage_manager(storage_manager)

        logger.info("✅ 存储管理器初始化完成")
        return storage_manager
    except Exception as e:
        logger.warning(f"⚠️ 存储管理器初始化失败: {e}")
        return None

app = typer.Typer(help="ComfyUI 任务处理系统")

async def start_api_server_async(host: str, port: int):
    """异步启动API服务器"""
    config = uvicorn.Config("api.server:app", host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def start_consumer_async():
    """异步启动Consumer"""
    await asyncio.sleep(3)  # 等待API服务器启动
    await start_consumer()

@app.command()
def api(
    host: str = typer.Option(DEFAULT_HOST, help="API服务器主机"),
    port: int = typer.Option(DEFAULT_PORT, help="API服务器端口")
):
    """只启动API服务器"""
    logger.info(f"🌐 启动API服务器: http://{host}:{port}")
    os.environ['TASK_API_URL'] = f"http://{host}:{port}/api"
    asyncio.run(start_api_server_async(host, port))

@app.command()
def consumer():
    """只启动Consumer"""
    logger.info("🔧 启动Consumer")
    asyncio.run(start_consumer())

@app.command()
def run(
    host: str = typer.Option(DEFAULT_HOST, help="API服务器主机"),
    port: int = typer.Option(DEFAULT_PORT, help="API服务器端口")
):
    """启动API服务器和Consumer（默认）"""
    init_storage()  # 初始化存储管理器
    logger.info("🚀 启动完整服务")
    os.environ['TASK_API_URL'] = f"http://{host}:{port}/api"

    async def run_both():
        try:
            await asyncio.gather(
                start_api_server_async(host, port),
                start_consumer_async()
            )
        except KeyboardInterrupt:
            logger.info("👋 收到中断信号，正在退出")

    logger.info("✅ 服务启动中，按 Ctrl+C 停止")
    asyncio.run(run_both())

if __name__ == "__main__":
    # 在应用启动前初始化存储管理器
    init_storage()

    import sys
    if len(sys.argv) == 1:
        sys.argv.append("run")
    app()
