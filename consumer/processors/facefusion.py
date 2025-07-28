"""
FaceFusion 任务处理器

处理 FaceSwap 任务，通过 HTTP API 调用 FaceFusion 服务
"""
import time
import asyncio
from datetime import datetime, timezone
from loguru import logger
from services.face_swap_service import face_swap_service, FaceSwapRequest


class FaceFusionProcessor:
    """FaceFusion 任务处理器 - 通过 API 调用处理 Face Swap"""

    def __init__(self):
        """初始化处理器"""
        self.face_swap_service = face_swap_service
        logger.info("FaceFusionProcessor 初始化完成")

    def process(self, task):
        """处理 FaceSwap 任务"""
        task_id = task.get("taskId")
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        source_channel = task.get("source_channel")

        logger.info(f"开始处理 FaceSwap 任务: {task_id}")
        logger.debug(f"任务参数验证:")
        logger.debug(f"  - taskId: {task_id}")
        logger.debug(f"  - params存在: {bool(params)}")
        logger.debug(f"  - input_data存在: {bool(input_data)}")
        logger.debug(f"  - source_channel: {source_channel}")

        # 验证必需参数
        # 从 wf_json 中获取参数（统一格式）
        wf_json = input_data.get("wf_json", {})
        logger.debug(f"  - wf_json存在: {bool(wf_json)}")
        logger.debug(f"  - wf_json内容: {wf_json}")
        source_url = wf_json.get("source_url")
        target_url = wf_json.get("target_url")
        resolution = wf_json.get("resolution", "1024x1024")
        media_type = wf_json.get("media_type", "image")  # image 或 video
        model = wf_json.get("model", "inswapper_128_fp16")  # 模型参数

        if not task_id:
            logger.error("任务ID为空，无法处理")
            return None

        if not source_url or not target_url:
            logger.error(
                f"缺少必需参数: source_url={source_url}, target_url={target_url}")
            logger.error(f"请确保参数在 params.input_data.wf_json 路径下")
            self._update_task_status(
                task_id, "FAILED", message="缺少源图像或目标文件URL", source_channel=source_channel)
            return None

        try:
            # 记录任务开始时间
            task_started_at = datetime.now(timezone.utc)

            # 更新任务状态为 PROCESSING
            self._update_task_status(
                task_id, "PROCESSING", started_at=task_started_at, source_channel=source_channel)

            # 执行 FaceSwap 处理
            logger.info(f"🎯 开始执行 FaceSwap: {task_id}")
            t_start = time.time()

            # 创建异步事件循环并执行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(
                    self._execute_faceswap_task_async(
                        task_id=task_id,
                        source_url=source_url,
                        target_url=target_url,
                        resolution=resolution,
                        model=model,
                        task_started_at=task_started_at,
                        source_channel=source_channel
                    )
                )
            finally:
                loop.close()

            execution_time = time.time() - t_start
            logger.info(f"FaceSwap 处理耗时: {execution_time:.2f} 秒")

            # 根据结果更新任务状态
            if results and len(results) > 0:
                logger.info(f"✅ 任务执行成功，生成了 {len(results)} 个结果")

                update_success = self._update_task_status(
                    task_id, "COMPLETED",
                    output_data={"urls": results},
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
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
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
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
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
                )
            except Exception as update_error:
                logger.error(f"更新任务状态时也发生异常: {str(update_error)}")

            return None

    async def _execute_faceswap_task_async(self, task_id, source_url, target_url, 
                                          resolution, model, task_started_at, source_channel):
        """异步执行 FaceSwap 任务"""
        logger.info(f"📤 调用 Face Swap API...")
        
        # 更新状态
        self._update_task_status(task_id, "PROCESSING", message="调用换脸服务中...",
                                started_at=task_started_at, source_channel=source_channel)

        # 创建请求
        request = FaceSwapRequest(
            source_url=source_url,
            target_url=target_url,
            resolution=resolution,
            model=model
        )

        # 调用 Face Swap 服务
        try:
            response = await self.face_swap_service.process_face_swap(request)
            
            if response.status == "success" and response.output_path:
                logger.info(f"✅ Face Swap API 调用成功: {response.output_path}")
                
                # 下载并上传结果到云存储
                results = await self._download_and_upload_results(
                    response, task_id, task_started_at, source_channel
                )
                
                logger.info(f"📤 处理完成，共 {len(results)} 个文件")
                return results
            else:
                error_msg = response.error or "Face swap processing failed"
                logger.error(f"❌ Face Swap API 返回失败: {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ 调用 Face Swap API 失败: {e}")
            raise

    async def _download_and_upload_results(self, response, task_id, task_started_at, source_channel):
        """下载 Face Swap 结果并上传到云存储"""
        import httpx
        import tempfile
        import os
        from pathlib import Path
        from core.storage.manager import get_storage_manager
        
        results = []
        storage_manager = get_storage_manager()
        
        # 更新状态
        self._update_task_status(task_id, "PROCESSING", message="上传结果文件中...",
                                started_at=task_started_at, source_channel=source_channel)
        
        # 构建要处理的文件列表
        files_to_process = []
        
        # 主输出文件
        if response.output_path.startswith("http"):
            files_to_process.append({
                'url': response.output_path,
                'type': 'main'
            })
        else:
            # 如果是相对路径，构建完整 URL
            from config.settings import FACE_SWAP_API_URL
            files_to_process.append({
                'url': f"{FACE_SWAP_API_URL}{response.output_path}",
                'type': 'main'
            })
        
        # 额外的输出格式（如 GIF、WebP）
        if response.metadata:
            for key in ["gif_url", "webp_url"]:
                if key in response.metadata and response.metadata[key]:
                    files_to_process.append({
                        'url': response.metadata[key],
                        'type': key.replace('_url', '')
                    })
        
        # 下载并上传每个文件
        async with httpx.AsyncClient(timeout=30.0) as client:
            for file_info in files_to_process:
                try:
                    # 下载文件
                    logger.info(f"📥 下载文件: {file_info['url']}")
                    response = await client.get(file_info['url'])
                    response.raise_for_status()
                    
                    # 确定文件扩展名
                    url_path = file_info['url'].split('?')[0]
                    ext = Path(url_path).suffix or '.jpg'
                    
                    # 生成文件名
                    filename = f"faceswap_{task_id}_{file_info['type']}{ext}"
                    
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name
                    
                    try:
                        # 上传到云存储
                        logger.info(f"📤 上传到云存储: {filename}")
                        
                        # 读取文件内容
                        with open(tmp_path, 'rb') as f:
                            file_content = f.read()
                        
                        # 确定内容类型
                        content_type = "image/jpeg"
                        if ext in ['.mp4', '.mov']:
                            content_type = "video/mp4"
                        elif ext == '.gif':
                            content_type = "image/gif"
                        elif ext == '.webp':
                            content_type = "image/webp"
                        elif ext == '.png':
                            content_type = "image/png"
                        
                        # 上传文件
                        url = storage_manager.upload_binary(file_content, filename)
                        
                        if url:
                            logger.info(f"✅ 文件上传成功: {url}")
                            results.append(url)
                        else:
                            logger.error(f"❌ 文件上传失败: 返回 None")
                            # 如果上传失败，返回原始 URL
                            results.append(file_info['url'])
                    
                    finally:
                        # 清理临时文件
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                
                except Exception as e:
                    logger.error(f"处理文件时出错 {file_info['url']}: {e}")
                    # 如果处理失败，返回原始 URL
                    results.append(file_info['url'])
        
        return results

    def _update_task_status(self, task_id, status, message=None,
                            started_at=None, finished_at=None, output_data=None, source_channel=None):
        """更新任务状态"""
        import requests
        from config.settings import task_api_url

        logger.debug(f"🔄 更新任务状态: {task_id} -> {status}")
        if message:
            logger.debug(f"  消息: {message}")
        if output_data:
            logger.debug(f"  输出数据: {output_data}")
        logger.debug(f"  源渠道: {source_channel}")

        # 使用源渠道URL或回退到默认URL
        update_url = source_channel or task_api_url
        url = f"{update_url}/api/comm/task/update"
        logger.debug(f"  目标URL: {url}")
        logger.debug(f"  使用源渠道: {source_channel is not None}")

        payload = {
            "taskId": task_id,
            "status": status
        }

        if message:
            payload["task_message"] = message
        if started_at:
            formatted_started_at = started_at.strftime(
                "%Y-%m-%d %H:%M:%S") if isinstance(started_at, datetime) else started_at
            payload["started_at"] = formatted_started_at
        if finished_at:
            formatted_finished_at = finished_at.strftime(
                "%Y-%m-%d %H:%M:%S") if isinstance(finished_at, datetime) else finished_at
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