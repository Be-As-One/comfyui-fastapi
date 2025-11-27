"""
健康检查路由
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health/redis")
async def redis_health_check():
    """Redis健康检查"""
    from config.settings import TASK_MANAGER_TYPE

    if TASK_MANAGER_TYPE != 'redis':
        return {
            "status": "not_applicable",
            "message": "Redis模式未启用",
            "task_manager_type": TASK_MANAGER_TYPE
        }

    try:
        from config.redis_config import redis_config

        client = redis_config.get_client()
        client.ping()

        # 获取Redis信息
        info = client.info("server")
        memory_info = client.info("memory")

        return {
            "status": "healthy",
            "redis_version": info.get("redis_version"),
            "redis_mode": info.get("redis_mode"),
            "host": redis_config.host,
            "port": redis_config.port,
            "db": redis_config.db,
            "memory_used": memory_info.get("used_memory_human"),
            "memory_peak": memory_info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "message": "Redis连接失败"
            }
        )

@router.get("/status")
async def get_status():
    """获取服务状态"""
    from core.task_manager import get_task_stats
    from core.storage import get_storage_manager
    from config.settings import TASK_MANAGER_TYPE

    stats = get_task_stats()

    # 检查存储状态
    storage_status = "unknown"
    storage_providers = []
    try:
        storage_manager = get_storage_manager()
        if storage_manager.providers:
            storage_status = "available"
            storage_providers = list(storage_manager.providers.keys())
        else:
            storage_status = "no_providers"
    except RuntimeError:
        storage_status = "not_initialized"
    except Exception:
        storage_status = "error"

    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "task_manager_type": TASK_MANAGER_TYPE,
        "storage_status": storage_status,
        "storage_providers": storage_providers,
        **stats
    }
