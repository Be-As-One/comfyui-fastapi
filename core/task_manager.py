"""
任务管理器
"""
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from config.workflows import WORKFLOW_TEMPLATES
from config.environments import environment_manager


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

    def create_task(self, workflow_name: str = None, environment: str = None,
                    task_data: Dict[str, Any] = None, source_channel: str = None,
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # 确定任务的工作流名称和目标环境
        if workflow_name:
            # 检查是否是换脸工作流
            if workflow_name == "face_swap" or workflow_name == "faceswap":
                # 换脸任务处理
                environment_name = environment or "face_swap"
                target_port = 8000  # 换脸服务端口

                # 支持通过 params 或 task_data 传递参数
                if params and "input_data" in params:
                    task_data = params["input_data"]
                
                # 验证换脸任务数据
                if not task_data:
                    raise ValueError(
                        "Face swap tasks require task_data or params with input_data")

                required_fields = ["source_url", "target_url"]
                missing_fields = [field for field in required_fields
                                  if field not in task_data]
                if missing_fields:
                    raise ValueError(
                        f"Missing required fields: {missing_fields}")

                # 使用与ComfyUI相同的params.input_data.wf_json格式
                task = {
                    "taskId": task_id,
                    "workflow": workflow_name,  # 使用一致的键名
                    "workflow_name": workflow_name,  # 保持向后兼容
                    "environment": environment_name,
                    "target_port": target_port,
                    "params": {
                        "input_data": {
                            "wf_json": task_data  # 统一使用params.input_data.wf_json
                        }
                    },
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "status": "PENDING",
                    "source_channel": source_channel  # 添加源渠道信息
                }

                return task
            else:
                # 验证ComfyUI工作流是否存在
                available_workflows = environment_manager.get_all_workflows()
                if workflow_name not in available_workflows:
                    raise ValueError(
                        f"未知的工作流: {workflow_name}. 可用工作流: {available_workflows}")
        else:
            # 如果没有指定工作流，随机选择一个可用的工作流
            available_workflows = environment_manager.get_all_workflows()
            workflow_name = random.choice(
                available_workflows) if available_workflows else "basic_generation"

        # ComfyUI任务处理
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

        # 获取工作流对应的环境信息
        env_config = environment_manager.get_environment_by_workflow(
            workflow_name)
        environment_name = environment or (
            env_config.name if env_config else "comm")
        target_port = env_config.port if env_config else 3001

        task = {
            "taskId": task_id,
            "workflow": workflow_name,  # 使用一致的键名
            "workflow_name": workflow_name,  # 保持向后兼容
            "environment": environment_name,
            "target_port": target_port,
            "params": {
                "input_data": {
                    "wf_json": workflow
                }
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "PENDING",
            "source_channel": source_channel  # 添加源渠道信息
        }

        return task

    def get_next_task(self, workflow_names: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """获取下一个任务
        
        Args:
            workflow_names: 可选的工作流名称列表，用于筛选任务
        """
        # 如果没有指定工作流筛选，使用原有逻辑
        if not workflow_names:
            if not self.task_queue:
                # 队列为空时创建新任务
                task = self.create_task()
                self.task_queue.append(task)
                self.tasks_storage[task["taskId"]] = task

            task = self.task_queue.pop(0)
            task["status"] = "FETCHED"
            self.tasks_storage[task["taskId"]] = task
            return task
        
        # 如果指定了工作流筛选，查找匹配的任务
        for i, task in enumerate(self.task_queue):
            task_workflow = task.get("workflow_name") or task.get("workflow", "")
            
            # 检查任务的工作流是否在允许列表中
            if task_workflow in workflow_names:
                # 找到匹配的任务，从队列中移除
                matched_task = self.task_queue.pop(i)
                matched_task["status"] = "FETCHED"
                self.tasks_storage[matched_task["taskId"]] = matched_task
                return matched_task
        
        # 没有找到匹配的任务
        # 尝试创建一个新的匹配任务（如果队列太小）
        if len(self.task_queue) < 5:
            # 随机选择一个允许的工作流创建新任务
            import random
            workflow_name = random.choice(workflow_names) if workflow_names else None
            if workflow_name:
                try:
                    new_task = self.create_task(workflow_name=workflow_name)
                    new_task["status"] = "FETCHED"
                    self.tasks_storage[new_task["taskId"]] = new_task
                    return new_task
                except:
                    pass  # 创建失败，返回None
        
        return None

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
