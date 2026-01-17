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
        """判断是否为VHS_VideoCombine节点"""
        return node_data.get("class_type") == "VHS_VideoCombine"

    def _parse_url_path(self, url_path: str) -> Optional[Dict[str, str]]:
        """解析URL路径以提取文件信息"""
        try:
            # 解析类似 "/view?filename=xxx&subfolder=xxx&type=xxx&format=xxx" 的URL
            if url_path.startswith("/view?"):
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(url_path)
                params = parse_qs(parsed.query)

                return {
                    "filename": params.get("filename", [""])[0],
                    "subfolder": params.get("subfolder", [""])[0],
                    "type": params.get("type", ["output"])[0],
                    "format": params.get("format", ["image/png"])[0]
                }
            return None
        except Exception as e:
            logger.error(f"解析URL路径失败: {url_path}, 错误: {str(e)}")
            return None

    def collect_results(self, node_id: str, node_data: Dict[str, Any], node_output: Dict[str, Any],
                       message_id: str, upload_tasks: List[Dict[str, Any]]) -> None:
        """收集VHS_VideoCombine节点的输出"""
        logger.debug(f"处理VHS_VideoCombine节点 {node_id} 的输出")
        logger.debug(f"节点输出数据: {node_output}")

        # VHS_VideoCombine 节点的输出可能在 gifs 或 widgets 中
        if "gifs" in node_output:
            # 处理 GIF/视频输出（标准输出格式）
            gifs = node_output["gifs"]
            logger.debug(f"VHS_VideoCombine节点 {node_id} 生成了 {len(gifs)} 个GIF/视频文件")

            for gif_info in gifs:
                try:
                    filename = gif_info["filename"]
                    subfolder = gif_info.get("subfolder", "")
                    folder_type = gif_info.get("type", "output")
                    format_type = gif_info.get("format", "image/gif")

                    # 处理图像和视频格式
                    if format_type and (format_type.startswith('image') or format_type.startswith('video')):
                        # 根据格式确定文件类型
                        file_type = 'video' if format_type.startswith('video') else 'image'
                        logger.debug(f"收集{file_type}文件: {filename} (格式: {format_type})")

                        # 生成上传路径
                        from datetime import datetime
                        import os
                        file_ext = os.path.splitext(filename)[1]
                        if not file_ext:
                            # 根据格式类型推断扩展名
                            if 'mp4' in format_type:
                                file_ext = '.mp4'
                            elif 'webm' in format_type:
                                file_ext = '.webm'
                            elif 'gif' in format_type:
                                file_ext = '.gif'
                            else:
                                file_ext = '.mp4'  # 默认使用mp4

                        path = f"{datetime.now():%Y%m%d}/{message_id}_vhs_{len(upload_tasks)}{file_ext}"

                        # 添加到上传任务列表
                        upload_tasks.append({
                            'type': file_type,
                            'filename': filename,
                            'subfolder': subfolder,
                            'folder_type': folder_type,
                            'path': path,
                            'node_id': node_id
                        })
                    else:
                        logger.debug(f"跳过不支持的格式: {format_type}")

                except Exception as e:
                    logger.error(f"收集VHS输出失败: {gif_info}, 错误: {str(e)}")
                    continue

        # 根据JavaScript代码，VHS_VideoCombine也可能在widgets中有输出
        # 检查是否有widgets数组属性
        if "widgets" in node_output and isinstance(node_output["widgets"], list):
            widgets = node_output["widgets"]
            logger.debug(f"VHS_VideoCombine节点 {node_id} 有 {len(widgets)} 个widgets")

            for widget in widgets:
                try:
                    widget_type = widget.get("type")
                    widget_value = widget.get("value")

                    if widget_type == "image" and widget_value:
                        # 处理image类型的widget
                        parsed_vals = self._parse_url_path(widget_value)
                        if parsed_vals and parsed_vals.get("filename"):
                            if parsed_vals.get("type") == "output":
                                logger.debug(f"收集widget图像: {parsed_vals['filename']}")

                                # 生成上传路径
                                from datetime import datetime
                                import os
                                file_ext = os.path.splitext(parsed_vals['filename'])[1] or '.png'
                                path = f"{datetime.now():%Y%m%d}/{message_id}_vhs_widget_{len(upload_tasks)}{file_ext}"

                                # 添加到上传任务列表
                                upload_tasks.append({
                                    'type': 'image',
                                    'filename': parsed_vals['filename'],
                                    'subfolder': parsed_vals.get('subfolder', ''),
                                    'folder_type': parsed_vals.get('type', 'output'),
                                    'path': path,
                                    'node_id': node_id
                                })

                    elif widget_type == "preview" and widget_value:
                        # 处理preview类型的widget
                        if isinstance(widget_value, dict) and "params" in widget_value:
                            params = widget_value["params"]
                            format_type = params.get("format", "")

                            # 处理图像和视频格式
                            if format_type.startswith('image') or format_type.startswith('video'):
                                filename = params.get("filename")
                                if filename:
                                    file_type = 'video' if format_type.startswith('video') else 'image'
                                    logger.debug(f"收集preview {file_type}: {filename}")

                                    # 生成上传路径
                                    from datetime import datetime
                                    import os
                                    file_ext = os.path.splitext(filename)[1]
                                    if not file_ext:
                                        if 'mp4' in format_type:
                                            file_ext = '.mp4'
                                        elif 'webm' in format_type:
                                            file_ext = '.webm'
                                        else:
                                            file_ext = '.png'

                                    path = f"{datetime.now():%Y%m%d}/{message_id}_vhs_preview_{len(upload_tasks)}{file_ext}"

                                    # 添加到上传任务列表
                                    upload_tasks.append({
                                        'type': file_type,
                                        'filename': filename,
                                        'subfolder': params.get('subfolder', ''),
                                        'folder_type': params.get('type', 'output'),
                                        'path': path,
                                        'node_id': node_id
                                    })
                            else:
                                logger.debug(f"跳过不支持的preview格式: {format_type}")

                except Exception as e:
                    logger.error(f"处理widget失败: {widget}, 错误: {str(e)}")
                    continue

        # 方式3（Fallback）：如果上面都没有收集到结果，尝试从节点配置的 filename_prefix 构造
        # 记录本次调用前的任务数，判断是否已收集到结果
        tasks_before = len([t for t in upload_tasks if t.get('node_id') == node_id])
        if tasks_before == 0:
            inputs = node_data.get("inputs", {})
            filename_prefix = inputs.get("filename_prefix", "")
            if filename_prefix and inputs.get("save_output", True):
                from datetime import datetime
                import os

                format_str = inputs.get("format", "video/h264-mp4")
                if 'mp4' in format_str or 'h264' in format_str:
                    file_ext = '.mp4'
                elif 'webm' in format_str:
                    file_ext = '.webm'
                elif 'gif' in format_str:
                    file_ext = '.gif'
                else:
                    file_ext = '.mp4'

                # 构造文件名: prefix + 00001 + ext
                filename = f"{filename_prefix}00001{file_ext}"
                path = f"{datetime.now():%Y%m%d}/{message_id}_vhs_{len(upload_tasks)}{file_ext}"

                upload_tasks.append({
                    'type': 'video',
                    'filename': filename,
                    'subfolder': '',
                    'folder_type': 'output',
                    'path': path,
                    'node_id': node_id
                })
                logger.debug(f"✓ VHS fallback 根据 filename_prefix 构造: {filename}")

    def get_result_type(self) -> str:
        """获取结果类型"""
        return "video"  # VHS_VideoCombine 主要用于视频合成


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

        # Fallback：如果上面都没有收集到结果，尝试从节点配置的 filename_prefix 构造
        tasks_for_this_node = len([t for t in upload_tasks if t.get('node_id') == node_id])
        if tasks_for_this_node == 0:
            inputs = node_data.get("inputs", {})
            filename_prefix = inputs.get("filename_prefix", "")
            if filename_prefix:
                from datetime import datetime
                import os

                # SaveVideo 默认输出 mp4
                file_ext = '.mp4'
                # 构造文件名: prefix + 00001 + ext
                filename = f"{filename_prefix}_00001{file_ext}"
                path = f"{datetime.now():%Y%m%d}/{message_id}_video_{len(upload_tasks)}{file_ext}"

                upload_tasks.append({
                    'type': 'video',
                    'filename': filename,
                    'subfolder': '',
                    'folder_type': 'output',
                    'path': path,
                    'node_id': node_id
                })
                logger.info(f"✓ SaveVideo fallback 根据 filename_prefix 构造: {filename}")
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

        logger.info(f"🔍 collect_workflow_results: 收到 {len(outputs)} 个输出节点, prompt有 {len(prompt)} 个节点")

        for node_id, node_output in outputs.items():
            # 获取节点配置数据
            node_data = prompt.get(node_id, {})
            class_type = node_data.get("class_type", "unknown")

            # 寻找合适的结果处理器
            handler = self.get_handler(node_data)
            if handler:
                logger.info(f"✓ 节点 {node_id} ({class_type}) -> {handler.__class__.__name__}")
                handler.collect_results(node_id, node_data, node_output, message_id, upload_tasks)
            else:
                logger.info(f"✗ 节点 {node_id} ({class_type}) 没有对应的处理器")

        logger.info(f"📦 collect_workflow_results 完成: 收集到 {len(upload_tasks)} 个上传任务")
        return upload_tasks