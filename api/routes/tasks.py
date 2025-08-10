"""
任务相关API路由
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from core.task_manager import task_manager
from config.environments import environment_manager

router = APIRouter()


class TaskUpdateRequest(BaseModel):
    taskId: str
    status: str
    task_message: str = None
    started_at: str = None
    finished_at: str = None
    output_data: Dict[str, Any] = None


class FaceSwapTaskRequest(BaseModel):
    """FaceSwap 任务创建请求"""
    source_url: str = Field(..., description="源人脸图像URL")
    target_url: str = Field(..., description="目标图像/视频URL")
    resolution: str = Field(default="1024x1024", description="输出分辨率")
    media_type: str = Field(default="image", description="媒体类型: image 或 video")


class UnifiedTaskRequest(BaseModel):
    """统一任务创建请求"""
    workflow_name: str = Field(..., description="工作流名称")
    params: Optional[Dict[str, Any]] = Field(default=None, description="任务参数")


@router.get("/comfyui-fetch-task")
async def fetch_task():
    """获取待处理任务"""
    task = task_manager.get_next_task()
    if not task:
        return {}
    return task


@router.post("/comfyui-update-task")
async def update_task(request: TaskUpdateRequest):
    """更新任务状态"""
    success = task_manager.update_task_status(
        task_id=request.taskId,
        status=request.status,
        message=request.task_message,
        started_at=request.started_at,
        finished_at=request.finished_at,
        output_data=request.output_data
    )

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"success": True, "message": "Task updated successfully"}


@router.get("/comm/task/fetch")
async def fetch_task_comm():
    """获取待处理任务 - 统一通信端点"""
    task = task_manager.get_next_task()
    if not task:
        return {
            "success": True,
            "code": 200,
            "message": "No tasks available",
            "data": None
        }

    return {
        "success": True,
        "code": 200,
        "message": "Task fetched successfully",
        "data": task
    }


@router.post("/comm/task/update")
async def update_task_comm(request: TaskUpdateRequest):
    """更新任务状态 - 统一通信端点"""
    success = task_manager.update_task_status(
        task_id=request.taskId,
        status=request.status,
        message=request.task_message,
        started_at=request.started_at,
        finished_at=request.finished_at,
        output_data=request.output_data
    )

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "code": 200,
        "message": "Task updated successfully"
    }


@router.get("/tasks")
async def list_tasks():
    """列出所有任务（调试用）"""
    return task_manager.get_all_tasks()


@router.post("/tasks/create")
async def create_unified_task(request: UnifiedTaskRequest):
    """统一的任务创建接口"""
    try:
        # 根据工作流类型验证参数
        if request.workflow_name == "faceswap":
            _validate_faceswap_params(request.params)

        task = task_manager.create_task(
            workflow_name=request.workflow_name,
            params=request.params
        )
        return {
            "success": True,
            "task": task,
            "message": f"{request.workflow_name} 任务创建成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/faceswap/create")
async def create_faceswap_task(request: FaceSwapTaskRequest):
    """创建 FaceSwap 任务（便捷接口）"""
    try:
        # 构建任务参数
        task_params = {
            "input_data": {
                "source_url": request.source_url,
                "target_url": request.target_url,
                "resolution": request.resolution,
                "media_type": request.media_type
            }
        }

        # 创建任务
        task = task_manager.create_task(
            workflow_name="faceswap",
            params=task_params
        )

        return {
            "success": True,
            "taskId": task["taskId"],
            "status": task["status"],
            "message": "FaceSwap 任务创建成功",
            "task": task
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/clear")
async def clear_tasks():
    """清空所有任务"""
    task_manager.clear_all_tasks()
    return {"message": "All tasks cleared"}


@router.get("/environments")
async def get_environments():
    """获取所有环境信息"""
    return environment_manager.get_environment_info()


@router.get("/workflows")
async def get_workflows():
    """获取所有可用的工作流"""
    return {
        "workflows": environment_manager.get_all_workflows(),
        "workflow_mapping": environment_manager.workflow_to_env
    }


@router.post("/tasks/create/{workflow_name}")
async def create_task_with_workflow(workflow_name: str):
    """创建指定工作流的任务（兼容接口）"""
    try:
        task = task_manager.create_task(workflow_name=workflow_name)
        return {
            "success": True,
            "task": task,
            "message": f"{workflow_name} 任务创建成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_task_stats():
    """获取任务统计信息"""
    tasks = task_manager.get_all_tasks()

    stats = {
        "total": len(tasks),
        "pending": len([t for t in tasks if t.get("status") == "PENDING"]),
        "fetched": len([t for t in tasks if t.get("status") == "FETCHED"]),
        "processing": len([t for t in tasks if t.get("status") == "PROCESSING"]),
        "completed": len([t for t in tasks if t.get("status") == "COMPLETED"]),
        "failed": len([t for t in tasks if t.get("status") == "FAILED"])
    }

    # 按工作流类型统计
    workflow_stats = {}
    for task in tasks:
        workflow_name = task.get("workflow_name", "unknown")
        if workflow_name not in workflow_stats:
            workflow_stats[workflow_name] = 0
        workflow_stats[workflow_name] += 1

    return {
        "success": True,
        "stats": stats,
        "workflow_stats": workflow_stats
    }


@router.get("/supported-workflows")
async def get_supported_workflows():
    """获取支持的工作流类型"""
    from consumer.processor_registry import processor_registry
    from utils.workflow_filter import workflow_filter

    return {
        "success": True,
        "allowed_workflows": workflow_filter.get_allowed_workflows(),
        "filter_stats": workflow_filter.get_filter_stats(),
        "available_processors": processor_registry.list_processors()
    }


def _validate_faceswap_params(params: Dict[str, Any]) -> None:
    """验证 FaceSwap 任务参数"""
    if not params:
        raise ValueError("FaceSwap 任务缺少参数")

    input_data = params.get("input_data", {})

    required_fields = ["source_url", "target_url"]
    for field in required_fields:
        if not input_data.get(field):
            raise ValueError(f"FaceSwap 任务缺少必需参数: {field}")

    # 验证 media_type
    media_type = input_data.get("media_type", "image")
    if media_type not in ["image", "video"]:
        raise ValueError(f"不支持的媒体类型: {media_type}")

    # 验证 URL 格式
    source_url = input_data.get("source_url")
    target_url = input_data.get("target_url")
    if not (source_url.startswith("http://") or source_url.startswith("https://")):
        raise ValueError("source_url 必须是有效的 HTTP URL")
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        raise ValueError("target_url 必须是有效的 HTTP URL")
