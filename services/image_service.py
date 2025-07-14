"""
图片处理服务
"""
import os
import time
import asyncio
import httpx
import urllib.parse
from pathlib import Path
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from httpx_retries import RetryTransport, Retry


class ImageService:
    """图片处理服务类"""
    
    def __init__(self):
        # ComfyUI的input目录路径
        self.comfyui_input_dir = Path("/workspace/ComfyUI/input")
        # HTTP客户端配置
        self.timeout = httpx.Timeout(timeout=60.0, connect=30.0)
        self.max_concurrent_downloads = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 创建标准的重试策略和传输层
        retry = Retry(total=3, backoff_factor=0.5)
        self.retry_transport = RetryTransport(retry=retry)
    
    def _generate_filename(self, image_url: str) -> str:
        """生成唯一的本地文件名"""
        parsed_url = urllib.parse.urlparse(image_url)
        original_filename = os.path.basename(parsed_url.path)
        
        if not original_filename or '.' not in original_filename:
            original_filename = f"image_{int(time.time())}.png"
        
        timestamp = int(time.time() * 1000)
        name, ext = os.path.splitext(original_filename)
        return f"{name}_{timestamp}{ext}"
    
    def _save_file(self, content: bytes, local_path: Path, filename: str) -> str:
        """保存文件并返回文件名"""
        with open(local_path, 'wb') as f:
            f.write(content)
        
        file_size = len(content)
        logger.info(f"✅ 图片下载成功: {filename}, 大小: {file_size} bytes")
        return filename
    
    def download_image(self, image_url: str, target_dir: Optional[Path] = None) -> str:
        """同步下载图片"""
        return asyncio.run(self.download_image_async(image_url, target_dir))
    
    def download_images_batch(self, image_urls: List[str], target_dir: Optional[Path] = None) -> Dict[str, str]:
        """同步批量下载图片"""
        return self.download_images_batch_sync(image_urls, target_dir)
    
    def is_remote_url(self, url):
        """
        检查是否为远程URL
        
        Args:
            url (str): 要检查的URL
            
        Returns:
            bool: 是否为远程URL
        """
        if not isinstance(url, str):
            return False
        return url.startswith("http://") or url.startswith("https://")
    
    def get_comfyui_input_dir(self):
        """
        获取ComfyUI input目录路径
        
        Returns:
            Path: ComfyUI input目录路径
        """
        return self.comfyui_input_dir
    
    def set_comfyui_input_dir(self, path):
        """
        设置ComfyUI input目录路径
        
        Args:
            path (str or Path): 新的目录路径
        """
        self.comfyui_input_dir = Path(path)
        logger.info(f"ComfyUI input目录已更新为: {self.comfyui_input_dir}")

    async def download_image_async(self, image_url: str, target_dir: Optional[Path] = None) -> str:
        """异步下载图片"""
        if target_dir is None:
            target_dir = self.comfyui_input_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        local_filename = self._generate_filename(image_url)
        local_path = target_dir / local_filename
        
        logger.debug(f"开始异步下载图片: {image_url} -> {local_path}")
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.retry_transport
            ) as client:
                response = await client.get(image_url, headers=self.headers)
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"警告：下载的文件可能不是图片，Content-Type: {content_type}")
                
                return self._save_file(response.content, local_path, local_filename)
                
        except httpx.HTTPError as e:
            logger.error(f"❌ 异步下载失败: {str(e)}")
            raise

    async def download_images_batch_async(self, image_urls: List[str], target_dir: Optional[Path] = None) -> Dict[str, str]:
        """
        异步批量下载图片
        
        Args:
            image_urls (list): 图片URL列表
            target_dir (Path, optional): 目标目录，默认使用ComfyUI input目录
            
        Returns:
            dict: {原始URL: 本地文件名} 的映射
        """
        if not image_urls:
            return {}
        
        if target_dir is None:
            target_dir = self.comfyui_input_dir
            
        logger.info(f"开始异步批量下载 {len(image_urls)} 张图片")
        
        # 使用信号量限制并发数量
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_with_semaphore(url: str) -> tuple:
            async with semaphore:
                try:
                    local_filename = await self.download_image_async(url, target_dir)
                    return url, local_filename, None
                except Exception as e:
                    logger.error(f"异步下载失败 {url}: {str(e)}")
                    return url, None, str(e)
        
        # 并发下载所有图片
        tasks = [download_with_semaphore(url) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        success_results = {}
        failed_urls = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"下载任务异常: {str(result)}")
                continue
                
            url, local_filename, error = result
            if error is None and local_filename:
                success_results[url] = local_filename
            else:
                failed_urls.append(url)
        
        if failed_urls:
            logger.warning(f"异步批量下载完成，{len(failed_urls)} 张图片下载失败: {failed_urls}")
        else:
            logger.info(f"✅ 异步批量下载全部成功，共 {len(success_results)} 张图片")
        
        return success_results

    def download_images_batch_sync(self, image_urls: List[str], target_dir: Optional[Path] = None) -> Dict[str, str]:
        """同步方式运行异步批量下载"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.download_images_batch_async(image_urls, target_dir))
                    return future.result()
            else:
                return asyncio.run(self.download_images_batch_async(image_urls, target_dir))
        except RuntimeError:
            return asyncio.run(self.download_images_batch_async(image_urls, target_dir))


# 创建全局服务实例
image_service = ImageService()
