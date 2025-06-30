"""
任务相关API路由
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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

@router.get("/tasks")
async def list_tasks():
    """列出所有任务（调试用）"""
    return task_manager.get_all_tasks()

@router.post("/tasks/create")
async def create_task(workflow_name: str = None):
    """手动创建新任务"""
    try:
        task = task_manager.create_task(workflow_name=workflow_name)
        return task
    except ValueError as e:
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
    """创建指定工作流的任务"""
    try:
        task = task_manager.create_task(workflow_name=workflow_name)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
