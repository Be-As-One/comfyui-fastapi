"""
任务管理器
"""
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from config.workflows import WORKFLOW_TEMPLATES

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks_storage: Dict[str, Dict] = {}
        self.task_queue: List[Dict] = []
        self._initialize_queue()
    
    def _initialize_queue(self):
        """初始化任务队列"""
        for _ in range(3):
            task = self.create_task()
            self.task_queue.append(task)
            self.tasks_storage[task["taskId"]] = task
    
    def create_task(self) -> Dict[str, Any]:
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # 使用默认工作流模板
        workflow = WORKFLOW_TEMPLATES["default"].copy()
        
        # 随机修改参数
        if "3" in workflow and workflow["3"]["class_type"] == "KSampler":
            workflow["3"]["inputs"]["seed"] = random.randint(1, 1000000)
        
        if "6" in workflow and workflow["6"]["class_type"] == "CLIPTextEncode":
            prompts = [
                "a beautiful landscape with mountains and rivers",
                "a cute cat sitting on a wooden table", 
                "abstract art with vibrant colors and shapes",
                "a peaceful garden with blooming flowers",
                "a modern city skyline at golden hour"
            ]
            workflow["6"]["inputs"]["text"] = random.choice(prompts)
        
        task = {
            "taskId": task_id,
            "params": {
                "input_data": {
                    "wf_json": workflow
                }
            },
            "created_at": datetime.now().isoformat(),
            "status": "PENDING"
        }
        
        return task
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个任务"""
        if not self.task_queue:
            # 队列为空时创建新任务
            task = self.create_task()
            self.task_queue.append(task)
            self.tasks_storage[task["taskId"]] = task
        
        task = self.task_queue.pop(0)
        task["status"] = "FETCHED"
        self.tasks_storage[task["taskId"]] = task
        
        return task
    
    def update_task_status(self, task_id: str, status: str, 
                          message: str = None, started_at: str = None,
                          finished_at: str = None, output_data: Dict = None) -> bool:
        """更新任务状态"""
        if task_id not in self.tasks_storage:
            return False
        
        task = self.tasks_storage[task_id]
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        
        if message:
            task["task_message"] = message
        if started_at:
            task["started_at"] = started_at
        if finished_at:
            task["finished_at"] = finished_at
        if output_data:
            task["output_data"] = output_data
        
        self.tasks_storage[task_id] = task
        return True
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务"""
        return {
            "tasks": list(self.tasks_storage.values()),
            "queue_length": len(self.task_queue)
        }
    
    def clear_all_tasks(self):
        """清空所有任务"""
        self.tasks_storage.clear()
        self.task_queue.clear()

def get_task_stats() -> Dict[str, Any]:
    """获取任务统计信息"""
    return {
        "tasks_in_queue": len(task_manager.task_queue),
        "total_tasks": len(task_manager.tasks_storage)
    }

# 全局任务管理器实例
task_manager = TaskManager()
