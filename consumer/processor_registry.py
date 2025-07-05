"""
处理器注册表

统一管理不同类型的任务处理器，支持智能分发
"""
from typing import Dict, Any, Optional
from loguru import logger


class ProcessorRegistry:
    """处理器注册表"""
    
    def __init__(self):
        self.processors: Dict[str, Any] = {}
        self._initialized = False
    
    def _initialize_processors(self):
        """延迟初始化处理器"""
        if self._initialized:
            return
        
        try:
            # 导入并注册 ComfyUI 处理器
            from consumer.processors.comfyui import ComfyUIProcessor
            self.processors["comfyui"] = ComfyUIProcessor()
            logger.info("✅ ComfyUI 处理器注册成功")
            
            # 导入并注册 FaceFusion 处理器
            from consumer.processors.facefusion import FaceFusionProcessor
            self.processors["facefusion"] = FaceFusionProcessor()
            logger.info("✅ FaceFusion 处理器注册成功")
            
            self._initialized = True
            logger.info("🎯 处理器注册表初始化完成")
            
        except ImportError as e:
            logger.error(f"❌ 处理器导入失败: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ 处理器注册失败: {e}")
            raise
    
    def get_processor(self, workflow_name: str) -> Optional[Any]:
        """根据工作流名称获取对应的处理器"""
        
        # 延迟初始化
        if not self._initialized:
            self._initialize_processors()
        
        # 智能分发逻辑
        processor_type = self._determine_processor_type(workflow_name)
        
        if processor_type not in self.processors:
            logger.error(f"❌ 未找到处理器类型: {processor_type}")
            return None
        
        processor = self.processors[processor_type]
        logger.debug(f"🎯 工作流 '{workflow_name}' 分发到 {processor_type} 处理器")
        
        return processor
    
    def _determine_processor_type(self, workflow_name: str) -> str:
        """根据工作流名称确定处理器类型"""
        
        if not workflow_name:
            logger.warning("⚠️ 工作流名称为空，默认使用 ComfyUI 处理器")
            return "comfyui"
        
        # FaceSwap 任务
        if workflow_name == "faceswap":
            return "facefusion"
        
        # ComfyUI 任务（默认或明确的 ComfyUI 工作流）
        if (workflow_name.startswith("comfyui_") or 
            workflow_name in ["basic_generation", "text_to_image", "image_to_image", "inpainting"]):
            return "comfyui"
        
        # 其他未知类型，默认使用 ComfyUI 处理器
        logger.warning(f"⚠️ 未知工作流类型 '{workflow_name}'，默认使用 ComfyUI 处理器")
        return "comfyui"
    
    def register_processor(self, processor_type: str, processor: Any):
        """动态注册新的处理器"""
        self.processors[processor_type] = processor
        logger.info(f"✅ 动态注册处理器: {processor_type}")
    
    def list_processors(self) -> Dict[str, str]:
        """列出所有已注册的处理器"""
        if not self._initialized:
            self._initialize_processors()
        
        return {
            processor_type: str(type(processor).__name__)
            for processor_type, processor in self.processors.items()
        }
    
    def get_supported_workflows(self) -> Dict[str, str]:
        """获取支持的工作流类型"""
        return {
            "faceswap": "facefusion",
            "comfyui_*": "comfyui",
            "basic_generation": "comfyui",
            "text_to_image": "comfyui",
            "image_to_image": "comfyui",
            "inpainting": "comfyui"
        }


# 全局处理器注册表实例
processor_registry = ProcessorRegistry()