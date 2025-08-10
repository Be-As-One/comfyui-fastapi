"""
工作流过滤器
用于控制每台机器能处理的工作流类型
"""
import fnmatch
from typing import List
from loguru import logger
from config import settings


class WorkflowFilter:
    """工作流过滤器"""
    
    def __init__(self):
        """初始化过滤器配置"""
        self.allowed_workflows = self._parse_workflow_list(settings.ALLOWED_WORKFLOWS)
        self.log_filtered = settings.LOG_FILTERED_TASKS
        
        logger.info("🔒 工作流过滤器初始化:")
        if self.allowed_workflows == ['*']:
            logger.info(f"  - 允许的工作流: 所有")
        else:
            logger.info(f"  - 允许的工作流: {self.allowed_workflows}")
        logger.info(f"  - 记录被过滤任务: {self.log_filtered}")
    
    def _parse_workflow_list(self, workflow_str: str) -> List[str]:
        """解析工作流列表字符串"""
        if not workflow_str:
            return []
        
        workflows = [w.strip() for w in workflow_str.split(',')]
        return [w for w in workflows if w]
    
    def is_workflow_allowed(self, workflow_name: str) -> bool:
        """
        检查工作流是否被允许
        
        Args:
            workflow_name: 工作流名称
            
        Returns:
            bool: True 表示允许，False 表示不允许
        """
        if not workflow_name:
            workflow_name = "default"
        
        # 如果允许列表为空或包含 "*"，允许所有
        if not self.allowed_workflows or "*" in self.allowed_workflows:
            allowed = True
        else:
            # 检查是否匹配允许列表中的任何模式
            allowed = False
            for pattern in self.allowed_workflows:
                if fnmatch.fnmatch(workflow_name, pattern):
                    allowed = True
                    break
        
        # 记录被过滤的任务
        if not allowed and self.log_filtered:
            logger.warning(f"🚫 工作流 '{workflow_name}' 不在允许列表中，被过滤")
        
        return allowed
    
    def get_allowed_workflows(self) -> List[str]:
        """获取允许的工作流列表"""
        return self.allowed_workflows
    
    def get_filter_stats(self) -> dict:
        """获取过滤器统计信息"""
        return {
            "allowed_count": len(self.allowed_workflows),
            "allowed_workflows": self.allowed_workflows,
            "allows_all": "*" in self.allowed_workflows
        }
    
    def reload_config(self):
        """重新加载配置（用于动态更新）"""
        self.allowed_workflows = self._parse_workflow_list(settings.ALLOWED_WORKFLOWS)
        self.log_filtered = settings.LOG_FILTERED_TASKS
        
        logger.info("♻️  工作流过滤器配置已重新加载")


# 全局过滤器实例
workflow_filter = WorkflowFilter()