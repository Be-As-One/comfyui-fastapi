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

@router.get("/comfyui-history")
async def get_queue_history(max_items: int = 100) -> Dict[str, Any]:
    """获取队列历史记录"""
    try:
        data = comfyui_service.get_queue_history(max_items)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取队列历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取队列历史失败: {str(e)}")

@router.post("/comfyui-interrupt")
async def interrupt_current_task() -> Dict[str, Any]:
    """中断当前正在执行的任务"""
    try:
        data = comfyui_service.interrupt_current_task()
        return {
            "success": True,
            "message": "当前任务中断成功",
            "data": data
        }
    except Exception as e:
        logger.error(f"中断当前任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"中断当前任务失败: {str(e)}")
