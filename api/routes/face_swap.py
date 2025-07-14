#!/usr/bin/env python3
"""
Face Swap API Routes
Provides REST endpoints for face swap functionality via FaceFusion integration
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from loguru import logger
from services.face_swap_service import (
    face_swap_service, FaceSwapRequest, FaceSwapResponse
)
from core.task_manager import task_manager
from services.media_service import media_service
from core.storage import get_storage_manager

router = APIRouter(prefix="/api/face-swap", tags=["face-swap"])


@router.get("/health")
async def face_swap_health() -> Dict[str, Any]:
    """Check face swap service health"""
    is_healthy = await face_swap_service.health_check()
    service_info = await face_swap_service.get_service_info()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "face_swap_service": service_info,
        "available": is_healthy
    }


@router.post("/process", response_model=FaceSwapResponse)
async def process_face_swap(request: FaceSwapRequest) -> FaceSwapResponse:
    """Process face swap directly via API call"""
    try:
        logger.info(f"Direct face swap request: {request.source_url} -> "
                   f"{request.target_url}")
        
        result = await face_swap_service.process_face_swap(request)
        
        # If successful and output path exists, upload to storage
        if result.status == "success" and result.output_path:
            try:
                # Upload result to configured storage
                local_path = f"/Users/hzy/Code/zhuilai/video-faceswap" \
                           f"{result.output_path}"
                storage_manager = get_storage_manager()
                upload_result = await storage_manager.upload_file(
                    local_path,
                    content_type="image/jpeg" if result.metadata and 
                    result.metadata.get("file_type") == "image" 
                    else "video/mp4"
                )
                
                if upload_result and upload_result.get("url"):
                    # Update result with storage URL
                    result.output_path = upload_result["url"]
                    if result.metadata:
                        result.metadata["storage_url"] = upload_result["url"]
                        result.metadata["storage_provider"] = \
                            upload_result.get("provider")
                    
            except Exception as storage_error:
                logger.warning(f"Failed to upload face swap result to storage: "
                             f"{storage_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Face swap processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-task")
async def create_face_swap_task(
    source_url: str,
    target_url: str,
    resolution: str = "1024x1024",
    model: str = "inswapper_128_fp16",
    environment: str = "face_swap"
) -> Dict[str, Any]:
    """Create a face swap task for queue processing"""
    try:
        # Create task using existing task manager
        task_data = {
            "source_url": source_url,
            "target_url": target_url,
            "resolution": resolution,
            "model": model
        }
        
        task = task_manager.create_task(
            workflow_name="face_swap",
            environment=environment,
            task_data=task_data
        )
        
        logger.info(f"Created face swap task {task.get('taskId')}")
        
        return {
            "task_id": task.get("taskId"),
            "status": task.get("status"),
            "workflow": "face_swap",
            "environment": environment,
            "created_at": task.get("created_at"),
            "input_data": task.get("params", {}).get("input_data")
        }
        
    except Exception as e:
        logger.error(f"Failed to create face swap task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def get_face_swap_workflows() -> Dict[str, Any]:
    """Get available face swap workflows and models"""
    return {
        "workflows": ["face_swap"],
        "models": [
            "inswapper_128_fp16",
            "inswapper_128",
            "simswap_256",
            "simswap_512"
        ],
        "resolutions": [
            "512x512",
            "1024x1024",
            "1280x720",
            "1920x1080"
        ],
        "supported_formats": {
            "input": ["jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"],
            "output": ["jpg", "png", "mp4"]
        }
    }


@router.get("/queue-status")
async def get_face_swap_queue_status() -> Dict[str, Any]:
    """Get face swap task queue status"""
    # Filter tasks for face swap workflow
    all_tasks_data = task_manager.get_all_tasks()
    all_tasks = all_tasks_data.get("tasks", [])
    
    face_swap_tasks = [
        task for task in all_tasks 
        if (task.get("workflow") == "face_swap" or 
            task.get("workflow_name") == "face_swap")
    ]
    
    status_counts = {}
    for task in face_swap_tasks:
        status = task.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_face_swap_tasks": len(face_swap_tasks),
        "status_breakdown": status_counts,
        "pending_tasks": status_counts.get("PENDING", 0),
        "processing_tasks": status_counts.get("PROCESSING", 0),
        "completed_tasks": status_counts.get("COMPLETED", 0),
        "failed_tasks": status_counts.get("FAILED", 0)
    }


@router.get("/tasks")
async def list_face_swap_tasks(limit: int = 10) -> Dict[str, Any]:
    """List recent face swap tasks"""
    all_tasks_data = task_manager.get_all_tasks()
    all_tasks = all_tasks_data.get("tasks", [])
    
    face_swap_tasks = [
        task for task in all_tasks 
        if (task.get("workflow") == "face_swap" or 
            task.get("workflow_name") == "face_swap")
    ]
    
    # Sort by creation time, most recent first
    face_swap_tasks.sort(
        key=lambda x: x.get("created_at", ""), 
        reverse=True
    )
    
    # Apply limit
    recent_tasks = face_swap_tasks[:limit]
    
    return {
        "tasks": [
            {
                "task_id": task.get("taskId"),
                "status": task.get("status"),
                "workflow": task.get("workflow") or task.get("workflow_name"),
                "environment": task.get("environment"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
                "input_data": task.get("params", {}).get("input_data"),
                "result": task.get("output_data")
            }
            for task in recent_tasks
        ],
        "total": len(face_swap_tasks),
        "showing": len(recent_tasks)
    }