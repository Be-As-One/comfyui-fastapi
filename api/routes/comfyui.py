"""
ComfyUI 相关API路由
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from loguru import logger
from services.comfyui_service import comfyui_service

router = APIRouter()

@router.get("/comfyui-queue-status")
async def get_queue_status() -> Dict[str, Any]:
    """获取ComfyUI队列状态"""
    try:
        data = comfyui_service.get_queue_status()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取队列状态失败: {str(e)}")

@router.get("/comfyui-system-stats")
async def get_system_stats() -> Dict[str, Any]:
    """获取ComfyUI系统统计信息"""
    try:
        data = comfyui_service.get_system_stats()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")

@router.get("/comfyui-server-info")
async def get_server_info() -> Dict[str, Any]:
    """获取ComfyUI服务器信息"""
    try:
        data = comfyui_service.get_server_info()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取服务器信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取服务器信息失败: {str(e)}")
