"""
FaceFusion 任务处理器

处理 FaceSwap 任务，通过 HTTP API 调用 FaceFusion 服务
"""
import time
import asyncio
import httpx
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
from services.face_swap_service import face_swap_service, FaceSwapRequest
from core.storage.manager import get_storage_manager


class FaceFusionProcessor:
    """FaceFusion 任务处理器 - 通过 API 调用处理 Face Swap"""

    def __init__(self):
        self.face_swap_service = face_swap_service
        logger.info("FaceFusionProcessor 初始化完成")

    def process(self, task):
        """处理 FaceSwap 任务"""
        task_id = task.get("taskId")
        source_channel = task.get("source_channel")
        
        # 从 wf_json 中获取参数
        wf_json = task.get("params", {}).get("input_data", {}).get("wf_json", {})
        source_url = wf_json.get("source_url")
        target_url = wf_json.get("target_url")
        resolution = wf_json.get("resolution", "1024x1024")
        model = wf_json.get("model", "inswapper_128_fp16")

        if not all([task_id, source_url, target_url]):
            logger.error(f"缺少必需参数: task_id={task_id}, source_url={source_url}, target_url={target_url}")
            self._update_task_status(task_id, "FAILED", "缺少必需参数", source_channel)
            return None

        task_started_at = datetime.now(timezone.utc)
        
        try:
            # 更新状态为处理中
            self._update_task_status(task_id, "PROCESSING", started_at=task_started_at, source_channel=source_channel)
            
            # 调用 Face Swap API
            logger.info(f"🎯 开始执行 FaceSwap: {task_id}")
            results = asyncio.run(self._process_faceswap(
                task_id, source_url, target_url, resolution, model, task_started_at, source_channel
            ))
            
            if results:
                logger.info(f"✅ 任务执行成功: {task_id}")
                self._update_task_status(
                    task_id, "COMPLETED",
                    output_data={"urls": results},
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
                )
                return results
            else:
                raise Exception("No results generated")
                
        except Exception as e:
            logger.error(f"处理任务失败: {task_id}, 错误: {str(e)}")
            self._update_task_status(
                task_id, "FAILED",
                message=str(e),
                started_at=task_started_at,
                finished_at=datetime.now(timezone.utc),
                source_channel=source_channel
            )
            return None

    async def _process_faceswap(self, task_id, source_url, target_url, resolution, model, task_started_at, source_channel):
        """调用 Face Swap API 并上传结果"""
        # 创建请求
        request = FaceSwapRequest(
            source_url=source_url,
            target_url=target_url,
            resolution=resolution,
            model=model
        )
        
        # 调用服务
        response = await self.face_swap_service.process_face_swap(request)
        
        if response.status != "success" or not response.output_path:
            raise Exception(response.error or "Face swap processing failed")
        
        # 下载并上传结果
        results = []
        storage_manager = get_storage_manager()
        
        # 处理主输出和额外格式
        urls_to_process = [response.output_path]
        if response.metadata:
            urls_to_process.extend([
                response.metadata.get(key) 
                for key in ["gif_url", "webp_url"] 
                if response.metadata.get(key)
            ])
        
        # 确保 URL 是完整的
        from config.settings import FACE_SWAP_API_URL
        urls_to_process = [
            url if url.startswith("http") else f"{FACE_SWAP_API_URL}{url}"
            for url in urls_to_process
        ]
        
        # 下载并上传
        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx, url in enumerate(urls_to_process):
                try:
                    # 下载文件
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # 生成文件名
                    ext = Path(url.split('?')[0]).suffix or '.jpg'
                    filename = f"faceswap_{task_id}_{idx}{ext}"
                    
                    # 上传到云存储
                    upload_url = storage_manager.upload_binary(response.content, filename)
                    if upload_url:
                        results.append(upload_url)
                    else:
                        results.append(url)  # 失败时返回原始 URL
                        
                except Exception as e:
                    logger.error(f"处理文件失败 {url}: {e}")
                    results.append(url)  # 失败时返回原始 URL
        
        return results

    def _update_task_status(self, task_id, status, message=None, started_at=None, 
                           finished_at=None, output_data=None, source_channel=None):
        """更新任务状态"""
        import requests
        from config.settings import task_api_url
        
        if not task_id:
            return False
            
        url = f"{source_channel or task_api_url}/api/comm/task/update"
        
        payload = {
            "taskId": task_id,
            "status": status
        }
        
        if message:
            payload["task_message"] = message
        if started_at:
            payload["started_at"] = started_at.strftime("%Y-%m-%d %H:%M:%S")
        if finished_at:
            payload["finished_at"] = finished_at.strftime("%Y-%m-%d %H:%M:%S")
        if output_data:
            payload["output_data"] = output_data
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False