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


class VHS_VideoCombineResultHandler(ResultNodeHandler):
    """VHS_VideoCombine结果节点处理器"""

    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        return node_data.get("class_type") == "VHS_VideoCombine"

    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any],
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集VHS_VideoCombine节点的输出"""
        from datetime import datetime
        import os

        # 方式1：从 gifs 输出获取（标准方式）
        if node_output.get("gifs"):
            for gif_info in node_output["gifs"]:
                filename = gif_info.get("filename")
                if filename:
                    file_ext = os.path.splitext(filename)[1] or '.mp4'
                    upload_tasks.append({
                        'type': 'video',
                        'filename': filename,
                        'subfolder': gif_info.get("subfolder", ""),
                        'folder_type': gif_info.get("type", "output"),
                        'path': f"{datetime.now():%Y%m%d}/{message_id}_vhs_{len(upload_tasks)}{file_ext}",
                        'node_id': node_id
                    })
                    logger.debug(f"✓ VHS gifs 输出: {filename}")
            return

        # 方式2：从节点配置的 filename_prefix 构造（fallback）
        inputs = node_data.get("inputs", {})
        filename_prefix = inputs.get("filename_prefix", "")
        if filename_prefix and inputs.get("save_output", True):
            format_str = inputs.get("format", "video/h264-mp4")
            file_ext = '.mp4' if 'mp4' in format_str or 'h264' in format_str else '.webm' if 'webm' in format_str else '.gif' if 'gif' in format_str else '.mp4'

            # 构造文件名: prefix + 00001 + ext
            filename = f"{filename_prefix}00001{file_ext}"
            upload_tasks.append({
                'type': 'video',
                'filename': filename,
                'subfolder': '',
                'folder_type': 'output',
                'path': f"{datetime.now():%Y%m%d}/{message_id}_vhs_{len(upload_tasks)}{file_ext}",
                'node_id': node_id
            })
            logger.debug(f"✓ VHS fallback 构造: {filename}")

    def get_result_type(self) -> str:
        return "video"


class SaveVideoResultHandler(ResultNodeHandler):
    """SaveVideo结果节点处理器"""

    def can_handle(self, node_data: Dict[str, Any]) -> bool:
        """判断是否为SaveVideo节点"""
        return node_data.get("class_type") == "SaveVideo"

    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any],
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集SaveVideo节点的输出视频"""
        logger.debug(f"处理SaveVideo节点 {node_id} 的输出")
        logger.debug(f"SaveVideo节点输出数据: {node_output}")

        # SaveVideo节点的视频文件信息存储在 "images" 字段中（尽管是视频文件）
        # "animated" 字段只是布尔值标记，不包含文件信息
        # 也可能在 "videos" 或 "gifs" 字段中
        video_fields = ["images", "videos", "gifs"]

        for field in video_fields:
            if field in node_output:
                videos = node_output[field]

                # 确保是列表
                if not isinstance(videos, list):
                    logger.warning(f"SaveVideo节点 {node_id} 的 '{field}' 字段不是列表: {type(videos)}")
                    continue

                logger.debug(f"SaveVideo节点 {node_id} 在字段 '{field}' 中找到 {len(videos)} 个条目")

                for video_info in videos:
                    try:
                        # 检查是否是字典
                        if not isinstance(video_info, dict):
                            logger.debug(f"跳过非字典条目: {video_info}")
                            continue

                        filename = video_info.get("filename")
                        if not filename:
                            logger.debug(f"跳过缺少filename的条目: {video_info}")
                            continue

                        subfolder = video_info.get("subfolder", "")
                        folder_type = video_info.get("type", "output")

                        logger.debug(f"收集视频: {filename} (subfolder={subfolder}, type={folder_type})")

                        # 生成上传路径
                        from datetime import datetime
                        import os
                        file_ext = os.path.splitext(filename)[1] or '.mp4'
                        path = f"{datetime.now():%Y%m%d}/{message_id}_video_{len(upload_tasks)}{file_ext}"

                        # 添加到上传任务列表
                        upload_tasks.append({
                            'type': 'video',
                            'filename': filename,
                            'subfolder': subfolder,
                            'folder_type': folder_type,
                            'path': path,
                            'node_id': node_id
                        })

                    except Exception as e:
                        logger.error(f"收集视频失败: {video_info}, 错误: {str(e)}")
                        continue

                # 只要找到有效的文件就返回
                if upload_tasks:
                    return

        logger.warning(f"SaveVideo节点 {node_id} 没有找到视频输出，可用字段: {list(node_output.keys())}")

    def get_result_type(self) -> str:
        """获取结果类型"""
        return "video"


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
        self.register(SaveVideoResultHandler())
        self.register(SaveAudioResultHandler())
        self.register(VHS_VideoCombineResultHandler())
    
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
        processed_nodes = set()

        # 1. 首先处理 outputs 中有输出的节点
        for node_id, node_output in outputs.items():
            node_data = prompt.get(node_id, {})
            handler = self.get_handler(node_data)
            if handler:
                logger.debug(f"找到结果处理器 {handler.__class__.__name__} 处理节点 {node_id}")
                handler.collect_results(node_id, node_data, node_output, message_id, upload_tasks)
                processed_nodes.add(node_id)
            else:
                class_type = node_data.get("class_type", "unknown")
                logger.debug(f"没有找到结果处理器处理节点 {node_id} (类型: {class_type})")

        # 2. 特殊处理：扫描 prompt 中的 VHS_VideoCombine 节点（可能不在 outputs 中）
        for node_id, node_data in prompt.items():
            if node_id in processed_nodes:
                continue

            class_type = node_data.get("class_type", "")
            if class_type == "VHS_VideoCombine":
                logger.debug(f"发现未处理的 VHS_VideoCombine 节点 {node_id}，尝试根据配置收集结果")
                handler = self.get_handler(node_data)
                if handler:
                    # 传入空的 node_output，让 handler 根据 node_data 构造文件信息
                    handler.collect_results(node_id, node_data, {}, message_id, upload_tasks)
                    processed_nodes.add(node_id)

        logger.debug(f"总共收集到 {len(upload_tasks)} 个结果任务")
        return upload_tasks