"""
FaceFusion 任务处理器

处理 FaceSwap 任务，调用 FaceFusion 核心功能
"""
import os
import sys
import json
import time
import requests
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

# 添加项目根目录到 Python 路径，确保能导入 main.py
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import ModelSwapper, convert_mp4


class FaceFusionProcessor:
    """FaceFusion 任务处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.model_swapper = None
        logger.info("FaceFusionProcessor 初始化完成")
    
    def _get_model_swapper(self):
        """懒加载 ModelSwapper，避免启动时初始化"""
        if self.model_swapper is None:
            logger.info("🔧 初始化 FaceFusion ModelSwapper...")
            self.model_swapper = ModelSwapper()
            logger.info("✅ ModelSwapper 初始化完成")
        return self.model_swapper
    
    def process(self, task):
        """处理 FaceSwap 任务"""
        task_id = task.get("taskId")
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        
        logger.info(f"开始处理 FaceSwap 任务: {task_id}")
        logger.debug(f"任务参数验证:")
        logger.debug(f"  - taskId: {task_id}")
        logger.debug(f"  - params存在: {bool(params)}")
        logger.debug(f"  - input_data存在: {bool(input_data)}")
        
        # 验证必需参数
        source_url = input_data.get("source_url")
        target_url = input_data.get("target_url")
        resolution = input_data.get("resolution", "1024x1024")
        media_type = input_data.get("media_type", "image")  # image 或 video
        
        if not task_id:
            logger.error("任务ID为空，无法处理")
            return None
            
        if not source_url or not target_url:
            logger.error(f"缺少必需参数: source_url={source_url}, target_url={target_url}")
            self._update_task_status(task_id, "FAILED", message="缺少源图像或目标文件URL")
            return None
        
        try:
            # 记录任务开始时间
            task_started_at = datetime.now(timezone.utc)
            
            # 更新任务状态为 PROCESSING
            self._update_task_status(task_id, "PROCESSING", started_at=task_started_at)
            
            # 执行 FaceSwap 处理
            logger.info(f"🎯 开始执行 FaceSwap: {task_id}")
            t_start = time.time()
            
            results = self._execute_faceswap_task(
                task_id=task_id,
                source_url=source_url, 
                target_url=target_url,
                resolution=resolution,
                media_type=media_type,
                task_started_at=task_started_at
            )
            
            execution_time = time.time() - t_start
            logger.info(f"FaceSwap 处理耗时: {execution_time:.2f} 秒")
            
            # 根据结果更新任务状态
            if results and len(results) > 0:
                logger.info(f"✅ 任务执行成功，生成了 {len(results)} 个结果")
                
                update_success = self._update_task_status(
                    task_id, "COMPLETED",
                    output_data={"urls": results},
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc)
                )
                
                if update_success:
                    logger.info(f"✅ 任务完成状态更新成功: {task_id}")
                else:
                    logger.error(f"❌ 更新任务完成状态失败: {task_id}")
                
                return results
            else:
                logger.error(f"❌ 任务执行失败：没有生成任何结果")
                
                self._update_task_status(
                    task_id, "FAILED",
                    message="No results generated.",
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc)
                )
                
                return None
                
        except Exception as e:
            logger.error(f"处理任务时发生异常: {task_id}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常消息: {str(e)}")
            logger.error(f"异常详情:", exc_info=True)
            
            try:
                self._update_task_status(
                    task_id, "FAILED",
                    message=str(e),
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc)
                )
            except Exception as update_error:
                logger.error(f"更新任务状态时也发生异常: {str(update_error)}")
            
            return None
    
    def _execute_faceswap_task(self, task_id, source_url, target_url, resolution, media_type, task_started_at):
        """执行 FaceSwap 任务"""
        logger.info(f"📁 开始下载源文件和目标文件...")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # 下载源图像
            source_ext = self._get_file_extension(source_url, "jpg")
            source_path = temp_dir_path / f"source.{source_ext}"
            logger.info(f"下载源图像: {source_url} -> {source_path}")
            self._download_file(source_url, source_path)
            
            # 下载目标文件
            target_ext = self._get_file_extension(target_url, "mp4" if media_type == "video" else "jpg")
            target_path = temp_dir_path / f"target.{target_ext}"
            logger.info(f"下载目标文件: {target_url} -> {target_path}")
            self._download_file(target_url, target_path)
            
            # 设置输出文件路径
            output_ext = target_ext  # 保持与目标文件相同的格式
            output_path = temp_dir_path / f"output.{output_ext}"
            
            # 执行 FaceSwap 处理
            logger.info(f"🔄 开始 FaceSwap 处理...")
            self._update_task_status(task_id, "PROCESSING", message="执行人脸交换中...", started_at=task_started_at)
            
            # 获取 ModelSwapper 实例并处理
            swapper = self._get_model_swapper()
            swapper.process(
                sources=[str(source_path)],
                target=str(target_path),
                output=str(output_path),
                resolution=resolution
            )
            
            # 检查输出文件是否存在
            if not output_path.exists():
                raise Exception(f"FaceSwap 处理失败：输出文件不存在 {output_path}")
            
            logger.info(f"✅ FaceSwap 处理完成: {output_path}")
            
            # 如果是视频，可选择转换为其他格式
            results = []
            
            # 上传主要结果
            logger.info(f"📤 上传处理结果...")
            self._update_task_status(task_id, "PROCESSING", message="上传结果文件中...", started_at=task_started_at)
            
            main_result_url = self._upload_file(output_path, f"faceswap_{task_id}_output.{output_ext}")
            results.append(main_result_url)
            
            # 如果是视频，额外生成 GIF 和 WebP 格式
            if media_type == "video" and output_ext == "mp4":
                try:
                    # 生成 GIF
                    gif_path = temp_dir_path / f"output.gif"
                    logger.info(f"🎬 转换为 GIF: {gif_path}")
                    convert_mp4(str(output_path), str(gif_path), "gif")
                    if gif_path.exists():
                        gif_url = self._upload_file(gif_path, f"faceswap_{task_id}_output.gif")
                        results.append(gif_url)
                    
                    # 生成 WebP
                    webp_path = temp_dir_path / f"output.webp"
                    logger.info(f"🎬 转换为 WebP: {webp_path}")
                    convert_mp4(str(output_path), str(webp_path), "webp")
                    if webp_path.exists():
                        webp_url = self._upload_file(webp_path, f"faceswap_{task_id}_output.webp")
                        results.append(webp_url)
                        
                except Exception as e:
                    logger.warning(f"⚠️ 视频格式转换失败，但主要结果已生成: {e}")
            
            logger.info(f"📤 上传完成，共 {len(results)} 个文件")
            return results
    
    def _download_file(self, url, local_path):
        """下载文件到本地"""
        try:
            logger.debug(f"下载文件: {url} -> {local_path}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"✅ 文件下载完成: {local_path}")
            
        except Exception as e:
            logger.error(f"❌ 下载文件失败: {url} -> {local_path}")
            logger.error(f"错误详情: {e}")
            raise Exception(f"下载文件失败: {url}")
    
    def _upload_file(self, file_path, filename):
        """上传文件到云存储"""
        try:
            from core.storage.manager import get_storage_manager
            
            storage_manager = get_storage_manager()
            if not storage_manager:
                raise Exception("存储管理器未初始化")
            
            logger.debug(f"上传文件: {file_path} -> {filename}")
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 上传到云存储
            result = storage_manager.upload(file_content, filename)
            
            if result and result.get('success'):
                url = result.get('url')
                logger.info(f"✅ 文件上传成功: {url}")
                return url
            else:
                raise Exception(f"上传失败: {result}")
                
        except Exception as e:
            logger.error(f"❌ 上传文件失败: {file_path}")
            logger.error(f"错误详情: {e}")
            raise Exception(f"上传文件失败: {filename}")
    
    def _get_file_extension(self, url, default="jpg"):
        """从URL获取文件扩展名"""
        try:
            path = Path(url)
            ext = path.suffix.lstrip('.')
            return ext if ext else default
        except:
            return default
    
    def _update_task_status(self, task_id, status, message=None, 
                           started_at=None, finished_at=None, output_data=None):
        """更新任务状态"""
        from config.settings import task_api_url
        
        logger.debug(f"🔄 更新任务状态: {task_id} -> {status}")
        if message:
            logger.debug(f"  消息: {message}")
        if output_data:
            logger.debug(f"  输出数据: {output_data}")
        
        url = f"{task_api_url}/comfyui-update-task"
        
        payload = {
            "taskId": task_id,
            "status": status
        }
        
        if message:
            payload["task_message"] = message
        if started_at:
            formatted_started_at = started_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(started_at, datetime) else started_at
            payload["started_at"] = formatted_started_at
        if finished_at:
            formatted_finished_at = finished_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(finished_at, datetime) else finished_at
            payload["finished_at"] = formatted_finished_at
        if output_data:
            payload["output_data"] = output_data
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            response_data = response.json()
            success = response_data.get("success", False)
            
            if success:
                logger.debug(f"✅ 任务状态更新成功: {task_id} -> {status}")
                return True
            else:
                logger.error(f"❌ API返回错误: {response_data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 更新任务状态失败: {task_id}")
            logger.error(f"错误详情: {e}")
            return False