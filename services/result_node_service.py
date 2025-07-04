"""
结果节点服务
处理工作流执行后的结果节点，如SaveImage、PreviewImage、SaveAudio等
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger


class ResultNodeHandler(ABC):
    """结果节点处理器基类"""
    
    @abstractmethod
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否能处理该结果节点"""
        pass
    
    @abstractmethod
    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any], 
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """
        收集结果节点的输出
        
        Args:
            node_id: 节点ID
            node_data: 节点配置数据
            node_output: 节点执行输出
            message_id: 消息ID
            upload_tasks: 上传任务列表（用于收集需要上传的资源）
        """
        pass
    
    @abstractmethod
    def get_result_type(self) -> str:
        """获取结果类型（如 'image', 'audio', 'video' 等）"""
        pass


class SaveImageResultHandler(ResultNodeHandler):
    """SaveImage结果节点处理器"""
    
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为SaveImage节点"""
        return node_data.get("class_type") == "SaveImage"
    
    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any], 
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集SaveImage节点的输出图像"""
        logger.debug(f"处理SaveImage节点 {node_id} 的输出")
        
        if "images" in node_output:
            images = node_output["images"]
            logger.debug(f"SaveImage节点 {node_id} 生成了 {len(images)} 张图像")
            
            for image_info in images:
                try:
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    folder_type = image_info.get("type", "output")
                    
                    logger.debug(f"收集图像: {filename}")
                    
                    # 生成上传路径
                    from datetime import datetime
                    path = f"{datetime.now():%Y%m%d}/{message_id}_{len(upload_tasks)}.png"
                    
                    # 添加到上传任务列表
                    upload_tasks.append({
                        'type': 'image',
                        'filename': filename,
                        'subfolder': subfolder,
                        'folder_type': folder_type,
                        'path': path,
                        'node_id': node_id
                    })
                    
                except Exception as e:
                    logger.error(f"收集图像失败: {filename}, 错误: {str(e)}")
                    continue
    
    def get_result_type(self) -> str:
        """获取结果类型"""
        return "image"


class PreviewImageResultHandler(ResultNodeHandler):
    """PreviewImage结果节点处理器"""
    
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为PreviewImage节点"""
        return node_data.get("class_type") == "PreviewImage"
    
    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any], 
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集PreviewImage节点的输出图像"""
        logger.debug(f"处理PreviewImage节点 {node_id} 的输出")
        
        if "images" in node_output:
            images = node_output["images"]
            logger.debug(f"PreviewImage节点 {node_id} 生成了 {len(images)} 张图像")
            
            for image_info in images:
                try:
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    folder_type = image_info.get("type", "temp")
                    
                    logger.debug(f"收集预览图像: {filename}")
                    
                    # 生成上传路径
                    from datetime import datetime
                    path = f"{datetime.now():%Y%m%d}/{message_id}_preview_{len(upload_tasks)}.png"
                    
                    # 添加到上传任务列表
                    upload_tasks.append({
                        'type': 'image',
                        'filename': filename,
                        'subfolder': subfolder,
                        'folder_type': folder_type,
                        'path': path,
                        'node_id': node_id
                    })
                    
                except Exception as e:
                    logger.error(f"收集预览图像失败: {filename}, 错误: {str(e)}")
                    continue
    
    def get_result_type(self) -> str:
        """获取结果类型"""
        return "image"


class SaveAudioResultHandler(ResultNodeHandler):
    """SaveAudio结果节点处理器"""
    
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为SaveAudio节点"""
        return node_data.get("class_type") == "SaveAudio"
    
    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any], 
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集SaveAudio节点的输出音频"""
        logger.debug(f"处理SaveAudio节点 {node_id} 的输出")
        
        if "audio" in node_output:
            audio_files = node_output["audio"]
            logger.debug(f"SaveAudio节点 {node_id} 生成了 {len(audio_files)} 个音频文件")
            
            for audio_info in audio_files:
                try:
                    filename = audio_info["filename"]
                    subfolder = audio_info.get("subfolder", "")
                    folder_type = audio_info.get("type", "output")
                    
                    logger.debug(f"收集音频: {filename}")
                    
                    # 生成上传路径
                    from datetime import datetime
                    # 保持音频文件的原始扩展名
                    import os
                    file_ext = os.path.splitext(filename)[1] or '.wav'
                    path = f"{datetime.now():%Y%m%d}/{message_id}_audio_{len(upload_tasks)}{file_ext}"
                    
                    # 添加到上传任务列表
                    upload_tasks.append({
                        'type': 'audio',
                        'filename': filename,
                        'subfolder': subfolder,
                        'folder_type': folder_type,
                        'path': path,
                        'node_id': node_id
                    })
                    
                except Exception as e:
                    logger.error(f"收集音频失败: {filename}, 错误: {str(e)}")
                    continue
        
        # 有些SaveAudio节点可能使用 "audios" 字段
        elif "audios" in node_output:
            audio_files = node_output["audios"]
            logger.debug(f"SaveAudio节点 {node_id} 生成了 {len(audio_files)} 个音频文件")
            
            for audio_info in audio_files:
                try:
                    filename = audio_info["filename"]
                    subfolder = audio_info.get("subfolder", "")
                    folder_type = audio_info.get("type", "output")
                    
                    logger.debug(f"收集音频: {filename}")
                    
                    # 生成上传路径
                    from datetime import datetime
                    import os
                    file_ext = os.path.splitext(filename)[1] or '.wav'
                    path = f"{datetime.now():%Y%m%d}/{message_id}_audio_{len(upload_tasks)}{file_ext}"
                    
                    # 添加到上传任务列表
                    upload_tasks.append({
                        'type': 'audio',
                        'filename': filename,
                        'subfolder': subfolder,
                        'folder_type': folder_type,
                        'path': path,
                        'node_id': node_id
                    })
                    
                except Exception as e:
                    logger.error(f"收集音频失败: {filename}, 错误: {str(e)}")
                    continue
    
    def get_result_type(self) -> str:
        """获取结果类型"""
        return "audio"


class ResultNodeService:
    """结果节点服务"""
    
    def __init__(self):
        self._handlers: List[ResultNodeHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认结果处理器"""
        self.register(SaveImageResultHandler())
        self.register(PreviewImageResultHandler())
        self.register(SaveAudioResultHandler())
    
    def register(self, handler: ResultNodeHandler) -> None:
        """注册结果处理器"""
        self._handlers.append(handler)
        logger.debug(f"注册结果节点处理器: {handler.__class__.__name__}")
    
    def get_handler(self, node_data: Dict[str, Any]) -> Optional[ResultNodeHandler]:
        """获取适合的结果处理器"""
        for handler in self._handlers:
            if handler.can_handle(node_data):
                return handler
        return None
    
    def collect_workflow_results(self, prompt: Dict[str, Any], outputs: Dict[str, Any], 
                               message_id: str) -> List[Dict[str, Any]]:
        """
        收集工作流的所有结果
        
        Args:
            prompt: 工作流提示数据
            outputs: 执行输出数据
            message_id: 消息ID
            
        Returns:
            List[Dict]: 上传任务列表
        """
        upload_tasks = []
        
        for node_id, node_output in outputs.items():
            # 获取节点配置数据
            node_data = prompt.get(node_id, {})
            
            # 寻找合适的结果处理器
            handler = self.get_handler(node_data)
            if handler:
                logger.debug(f"找到结果处理器 {handler.__class__.__name__} 处理节点 {node_id}")
                handler.collect_results(node_id, node_data, node_output, message_id, upload_tasks)
            else:
                class_type = node_data.get("class_type", "unknown")
                logger.debug(f"没有找到结果处理器处理节点 {node_id} (类型: {class_type})")
        
        logger.debug(f"总共收集到 {len(upload_tasks)} 个结果任务")
        return upload_tasks