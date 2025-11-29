"""
任务数据格式定义
与 z-image 端对齐的任务结构
"""
from typing import TypedDict, Optional, Dict, Any, Literal
from datetime import datetime


# 任务优先级类型
TaskPriority = Literal["vip", "normal", "guest"]

# 任务状态类型
TaskStatus = Literal["PENDING", "FETCHED", "PROCESSING", "COMPLETED", "FAILED"]


class TaskInputData(TypedDict, total=False):
    """任务输入数据"""
    wf_json: Dict[str, Any]  # 工作流 JSON 或换脸参数
    source_url: Optional[str]  # 换脸: 源图片
    target_url: Optional[str]  # 换脸: 目标图片
    resolution: Optional[str]  # 分辨率
    model: Optional[str]  # 模型名称


class TaskParams(TypedDict, total=False):
    """任务参数"""
    input_data: TaskInputData
    workflow_name: Optional[str]


class QueueTask(TypedDict, total=False):
    """
    队列任务格式 - 与 z-image 端对齐

    示例:
    {
        "taskId": "task_abc123",
        "userId": "user_xyz",
        "priority": "vip",
        "workflow": "faceswap",
        "params": {
            "input_data": {
                "source_url": "https://...",
                "target_url": "https://..."
            }
        },
        "callbackUrl": "https://z-image.com/api/task/callback",
        "createdAt": "2024-01-01T00:00:00Z"
    }
    """
    taskId: str
    userId: Optional[str]
    priority: TaskPriority
    workflow: str  # "faceswap" | "comfyui_xxx"
    params: TaskParams
    callbackUrl: Optional[str]  # 结果回调 URL
    createdAt: str  # ISO 格式时间戳


class TaskResult(TypedDict, total=False):
    """
    任务结果格式

    示例:
    {
        "taskId": "task_abc123",
        "status": "COMPLETED",
        "result": {
            "output_url": "https://cdn.../output.jpg",
            "duration": 12.5
        },
        "error": null,
        "completedAt": "2024-01-01T00:01:00Z"
    }
    """
    taskId: str
    status: TaskStatus
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    completedAt: str


def normalize_queue_task(raw_task: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化队列任务格式
    兼容不同来源的任务数据结构

    Args:
        raw_task: 原始任务数据

    Returns:
        标准化后的任务数据
    """
    # 任务 ID
    task_id = raw_task.get("taskId") or raw_task.get("task_id") or raw_task.get("id")

    # 工作流名称 (支持多种命名格式)
    workflow = (
        raw_task.get("workflowName") or  # API 格式 (camelCase)
        raw_task.get("workflow") or
        raw_task.get("workflow_name") or
        raw_task.get("params", {}).get("workflowName") or
        raw_task.get("params", {}).get("workflow_name") or
        "default"
    )

    # 参数
    params = raw_task.get("params", {})
    if "input_data" not in params:
        # 兼容旧格式: 直接放在 params 里的数据
        params = {"input_data": params}

    # 回调 URL
    callback_url = (
        raw_task.get("callbackUrl") or
        raw_task.get("callback_url") or
        raw_task.get("params", {}).get("callbackUrl")
    )

    return {
        "taskId": task_id,
        "userId": raw_task.get("userId") or raw_task.get("user_id"),
        "priority": raw_task.get("priority", "normal"),
        "workflow": workflow,
        "workflowName": workflow,  # 同时提供 camelCase 格式，兼容 comfyui.py
        "params": params,
        "callbackUrl": callback_url,
        "createdAt": raw_task.get("createdAt") or raw_task.get("created_at") or datetime.utcnow().isoformat(),
        # 保留原始数据以便调试
        "_raw": raw_task
    }
