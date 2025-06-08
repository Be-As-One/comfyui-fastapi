"""
健康检查路由
"""
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
async def get_status():
    """获取服务状态"""
    from core.task_manager import get_task_stats
    from core.storage import get_storage_manager

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
        "storage_status": storage_status,
        "storage_providers": storage_providers,
        **stats
    }
