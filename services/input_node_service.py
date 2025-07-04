"""
输入节点服务
处理工作流中的输入节点，如LoadImage、LoadAudio等
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from loguru import logger
from services.media_service import MediaType


class InputNodeHandler(ABC):
    """输入节点处理器基类"""
    
    @abstractmethod
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否能处理该节点"""
        pass
    
    @abstractmethod
    def get_remote_urls(self, node_id: str, node_data: Dict[str, Any]) -> List[Tuple[str, str, MediaType]]:
        """
        获取节点中的远程URL
        
        Returns:
            List[Tuple[str, str, MediaType]]: (URL, 字段名, 媒体类型) 的列表
        """
        pass
    
    @abstractmethod
    def update_local_path(self, node_data: Dict[str, Any], field_name: str, local_path: str) -> None:
        """更新节点中的本地路径"""
        pass
    
    @abstractmethod
    def get_expected_media_type(self) -> MediaType:
        """获取该节点处理的媒体类型"""
        pass


class LoadImageHandler(InputNodeHandler):
    """LoadImage节点处理器"""
    
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为LoadImage节点"""
        return node_data.get("class_type") == "LoadImage"
    
    def get_remote_urls(self, node_id: str, node_data: Dict[str, Any]) -> List[Tuple[str, str, MediaType]]:
        """获取LoadImage节点的远程URL"""
        from services.media_service import media_service
        
        urls = []
        inputs = node_data.get("inputs", {})
        image_url = inputs.get("image")
        
        if image_url and media_service.is_remote_url(image_url):
            # 检测媒体类型
            media_type = media_service.detect_media_type(image_url)
            if media_type != MediaType.IMAGE and media_type != MediaType.UNKNOWN:
                logger.warning(f"LoadImage节点 {node_id} 包含非图片文件: {image_url} (类型: {media_type.value})")
            
            logger.info(f"发现LoadImage节点 {node_id} 包含远程图片: {image_url}")
            urls.append((image_url, "image", MediaType.IMAGE))
        
        return urls
    
    def update_local_path(self, node_data: Dict[str, Any], field_name: str, local_path: str) -> None:
        """更新LoadImage节点的本地路径"""
        inputs = node_data.get("inputs", {})
        if field_name == "image":
            inputs["image"] = local_path
    
    def get_expected_media_type(self) -> MediaType:
        """获取该节点处理的媒体类型"""
        return MediaType.IMAGE


class LoadAudioHandler(InputNodeHandler):
    """LoadAudio节点处理器"""
    
    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为LoadAudio节点"""
        return node_data.get("class_type") == "LoadAudio"
    
    def get_remote_urls(self, node_id: str, node_data: Dict[str, Any]) -> List[Tuple[str, str, MediaType]]:
        """获取LoadAudio节点的远程URL"""
        from services.media_service import media_service
        
        urls = []
        inputs = node_data.get("inputs", {})
        audio_url = inputs.get("audio")
        
        if audio_url and media_service.is_remote_url(audio_url):
            # 检测媒体类型
            media_type = media_service.detect_media_type(audio_url)
            if media_type != MediaType.AUDIO and media_type != MediaType.UNKNOWN:
                logger.warning(f"LoadAudio节点 {node_id} 包含非音频文件: {audio_url} (类型: {media_type.value})")
            
            logger.info(f"发现LoadAudio节点 {node_id} 包含远程音频: {audio_url}")
            urls.append((audio_url, "audio", MediaType.AUDIO))
        
        return urls
    
    def update_local_path(self, node_data: Dict[str, Any], field_name: str, local_path: str) -> None:
        """更新LoadAudio节点的本地路径"""
        inputs = node_data.get("inputs", {})
        if field_name == "audio":
            inputs["audio"] = local_path
    
    def get_expected_media_type(self) -> MediaType:
        """获取该节点处理的媒体类型"""
        return MediaType.AUDIO


class InputNodeService:
    """输入节点服务"""
    
    def __init__(self):
        self._handlers: List[InputNodeHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.register(LoadImageHandler())
        self.register(LoadAudioHandler())
    
    def register(self, handler: InputNodeHandler) -> None:
        """注册处理器"""
        self._handlers.append(handler)
        logger.debug(f"注册输入节点处理器: {handler.__class__.__name__}")
    
    def get_handler(self, node_data: Dict[str, Any]) -> Optional[InputNodeHandler]:
        """获取适合的处理器"""
        for handler in self._handlers:
            if handler.can_handle(node_data):
                return handler
        return None
    
    def collect_remote_urls(self, wf_json: Dict[str, Any]) -> Tuple[List[str], Dict[str, List[Tuple[str, str, str, Dict[str, Any], MediaType]]]]:
        """
        收集工作流中所有的远程URL
        
        Args:
            wf_json: 工作流JSON
            
        Returns:
            Tuple[List[str], Dict]: (所有URL列表, URL到节点信息的映射)
                映射格式: {url: [(node_id, field_name, handler_class, node_data, media_type), ...]}
        """
        remote_urls = []
        url_to_node_mapping = {}
        
        for node_id, node_data in wf_json.items():
            if not isinstance(node_data, dict):
                logger.debug(f"跳过非字典节点: {node_id}")
                continue
            
            class_type = node_data.get("class_type", "unknown")
            logger.debug(f"处理节点 {node_id}, 类型: {class_type}")
            
            handler = self.get_handler(node_data)
            if handler:
                logger.debug(f"找到处理器 {handler.__class__.__name__} 处理节点 {node_id}")
                urls = handler.get_remote_urls(node_id, node_data)
                logger.debug(f"节点 {node_id} 包含 {len(urls)} 个远程URL")
                
                for url, field_name, media_type in urls:
                    remote_urls.append(url)
                    if url not in url_to_node_mapping:
                        url_to_node_mapping[url] = []
                    url_to_node_mapping[url].append((
                        node_id,
                        field_name,
                        handler.__class__.__name__,
                        node_data,
                        media_type
                    ))
            else:
                logger.debug(f"没有找到处理器处理节点 {node_id} (类型: {class_type})")
        
        logger.debug(f"总共收集到 {len(remote_urls)} 个远程URL")
        return remote_urls, url_to_node_mapping
    
    def update_workflow_paths(self, wf_json: Dict[str, Any], download_results: Dict[str, str], 
                            url_to_node_mapping: Dict[str, List[Tuple[str, str, str, Dict[str, Any], MediaType]]]) -> None:
        """
        使用下载结果更新工作流中的路径
        
        Args:
            wf_json: 工作流JSON
            download_results: {url: local_path} 的映射
            url_to_node_mapping: URL到节点信息的映射
        """
        from services.media_service import media_service
        
        logger.debug(f"开始更新 {len(download_results)} 个下载结果的路径")
        
        for url, local_path in download_results.items():
            logger.debug(f"处理URL: {url} -> 本地路径: {local_path}")
            
            if url in url_to_node_mapping:
                logger.debug(f"URL {url} 映射到 {len(url_to_node_mapping[url])} 个节点")
                
                for node_id, field_name, _, node_data, expected_media_type in url_to_node_mapping[url]:
                    logger.debug(f"更新节点 {node_id} 的 {field_name} 字段")
                    
                    handler = self.get_handler(node_data)
                    if handler:
                        # 验证下载的文件类型是否正确
                        if not media_service.validate_media_file(local_path, expected_media_type):
                            logger.warning(f"⚠️  节点 {node_id} 的文件类型验证失败: {local_path}")
                        
                        handler.update_local_path(node_data, field_name, local_path)
                        logger.info(f"✅ 节点 {node_id} 的 {field_name} 路径已更新: {local_path}")
                    else:
                        logger.warning(f"⚠️  找不到处理器来更新节点 {node_id}")
            else:
                logger.warning(f"⚠️  URL {url} 没有对应的节点映射")