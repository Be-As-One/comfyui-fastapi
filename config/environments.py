"""
环境配置管理模块
"""
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger

class EnvironmentConfig:
    """环境配置类"""
    
    def __init__(self, name: str, description: str, port: int, workflows: List[str], 
                 nodes: List[str], models: List[Dict]):
        self.name = name
        self.description = description
        self.port = port
        self.workflows = workflows
        self.nodes = nodes
        self.models = models

class EnvironmentManager:
    """环境配置管理器"""
    
    def __init__(self, config_dir: str = "/config/environments"):
        self.config_dir = Path(config_dir)
        self.environments: Dict[str, EnvironmentConfig] = {}
        self.workflow_to_env: Dict[str, str] = {}
        self._load_environments()
    
    def _load_environments(self):
        """加载所有环境配置"""
        logger.info("🔧 加载环境配置...")
        
        if not self.config_dir.exists():
            logger.warning(f"环境配置目录不存在: {self.config_dir}")
            return
        
        # 加载所有 JSON 配置文件
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                env_config = EnvironmentConfig(
                    name=config_data.get("name"),
                    description=config_data.get("description", ""),
                    port=config_data.get("port", 3001),
                    workflows=config_data.get("workflows", []),
                    nodes=config_data.get("nodes", []),
                    models=config_data.get("models", [])
                )
                
                self.environments[env_config.name] = env_config
                
                # 建立工作流到环境的映射
                for workflow in env_config.workflows:
                    self.workflow_to_env[workflow] = env_config.name
                
                logger.info(f"✅ 加载环境配置: {env_config.name} (端口: {env_config.port}, 工作流: {len(env_config.workflows)})")
                
            except Exception as e:
                logger.error(f"❌ 加载环境配置文件 {config_file} 失败: {e}")
    
    def get_environment_by_workflow(self, workflow_name: str) -> Optional[EnvironmentConfig]:
        """根据工作流名称获取环境配置"""
        env_name = self.workflow_to_env.get(workflow_name)
        if env_name:
            return self.environments.get(env_name)
        return None
    
    def get_environment_by_name(self, env_name: str) -> Optional[EnvironmentConfig]:
        """根据环境名称获取环境配置"""
        return self.environments.get(env_name)
    
    def get_port_by_workflow(self, workflow_name: str) -> int:
        """根据工作流名称获取对应的端口"""
        env = self.get_environment_by_workflow(workflow_name)
        return env.port if env else 3001  # 默认端口
    
    def get_port_by_environment(self, env_name: str) -> int:
        """根据环境名称获取端口"""
        env = self.get_environment_by_name(env_name)
        return env.port if env else 3001  # 默认端口
    
    def get_comfyui_url_by_workflow(self, workflow_name: str, host: str = "127.0.0.1") -> str:
        """根据工作流名称获取ComfyUI服务器URL"""
        port = self.get_port_by_workflow(workflow_name)
        return f"http://{host}:{port}"
    
    def get_all_environments(self) -> Dict[str, EnvironmentConfig]:
        """获取所有环境配置"""
        return self.environments
    
    def get_all_workflows(self) -> List[str]:
        """获取所有可用的工作流"""
        return list(self.workflow_to_env.keys())
    
    def get_environment_info(self) -> Dict:
        """获取环境信息总览"""
        return {
            "total_environments": len(self.environments),
            "total_workflows": len(self.workflow_to_env),
            "environments": {
                name: {
                    "description": env.description,
                    "port": env.port,
                    "workflows": env.workflows,
                    "nodes_count": len(env.nodes),
                    "models_count": len(env.models)
                }
                for name, env in self.environments.items()
            },
            "workflow_mapping": self.workflow_to_env
        }

# 创建全局环境管理器实例
environment_manager = EnvironmentManager()