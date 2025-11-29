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

# 初始化 Google Cloud 认证
def init_google_cloud_auth():
    """初始化 Google Cloud 认证"""
    import os
    import base64
    import json
    
    try:
        # 从环境变量中读取 Base64 编码的凭据
        credentials_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if credentials_base64 and credentials_path:
            logger.info("🔧 解码 Base64 编码的 Google Cloud 凭据")
            decoded = base64.b64decode(credentials_base64).decode("utf-8")
            
            # 验证 JSON 格式
            json.loads(decoded)
            
            # 写入到指定的凭据文件路径
            with open(credentials_path, 'w', encoding='utf-8') as f:
                f.write(decoded)
            
            logger.info(f"✅ Google Cloud 认证文件已创建: {credentials_path}")
            return credentials_path
        
        # 检查是否已经设置了 GOOGLE_APPLICATION_CREDENTIALS 且文件存在
        if credentials_path and os.path.exists(credentials_path):
            logger.info(f"✅ 使用现有的 Google Cloud 认证文件: {credentials_path}")
            return credentials_path
        
        logger.warning("⚠️ 未找到 Google Cloud 认证配置，存储功能可能受限")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Google Cloud 凭据 JSON 格式错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 初始化 Google Cloud 认证失败: {e}")
        return None

# 初始化存储管理器
def init_storage():
    """初始化存储管理器（现在是自动的，这里只做预热）"""
    try:
        # 先初始化 Google Cloud 认证（如果使用 GCS）
        init_google_cloud_auth()

        # 触发存储管理器自动配置（懒加载）
        from core.storage import get_storage_manager
        storage_manager = get_storage_manager()

        if storage_manager.is_initialized():
            logger.info(f"✅ 存储管理器已就绪: {list(storage_manager.providers.keys())}")
        else:
            logger.warning("⚠️ 存储管理器未配置任何提供商")

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
    logger.info("🔄 准备启动 Consumer，将等待 ComfyUI 服务就绪...")
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
    # 初始化认证和存储
    init_storage()
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
