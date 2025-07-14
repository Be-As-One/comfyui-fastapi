"""
图片处理服务
"""
import os
import time
import httpx
import urllib.parse
from pathlib import Path
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        # 使用httpx同步客户端 + 重试传输层
        retry = Retry(total=3, backoff_factor=0.1)
        retry_transport = RetryTransport(retry=retry)
        
        self.client = httpx.Client(
            timeout=self.timeout,
            transport=retry_transport,
            headers=self.headers,
            follow_redirects=True
        )
    
    def _generate_filename(self, image_url: str) -> str:
        """生成唯一的本地文件名"""
        parsed_url = urllib.parse.urlparse(image_url)
        original_filename = os.path.basename(parsed_url.path)
        
        if not original_filename or '.' not in original_filename:
            original_filename = f"image_{int(time.time())}.png"
        
        timestamp = int(time.time() * 1000)
        name, ext = os.path.splitext(original_filename)
        return f"{name}_{timestamp}{ext}"
    
    
    def download_image(self, image_url: str, target_dir: Optional[Path] = None) -> str:
        """下载单个图片"""
        if target_dir is None:
            target_dir = self.comfyui_input_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        local_filename = self._generate_filename(image_url)
        local_path = target_dir / local_filename
        
        logger.debug(f"开始下载图片: {image_url} -> {local_path}")
        
        try:
            # 使用httpx同步客户端（不涉及事件循环，自动重试）
            with self.client.stream('GET', image_url) as response:
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"警告：下载的文件可能不是图片，Content-Type: {content_type}")
                
                # 流式写入文件
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            
            file_size = local_path.stat().st_size
            logger.info(f"✅ 图片下载成功: {local_filename}, 大小: {file_size} bytes")
            return local_filename
            
        except Exception as e:
            logger.error(f"❌ 下载失败 {image_url}: {str(e)}")
            raise
    
    def download_images_batch(self, image_urls: List[str], target_dir: Optional[Path] = None) -> Dict[str, str]:
        """批量下载图片（使用线程池）"""
        if not image_urls:
            return {}
        
        logger.info(f"开始批量下载 {len(image_urls)} 张图片")
        results = {}
        failed_urls = []
        
        def download_single(url: str) -> tuple:
            try:
                filename = self.download_image(url, target_dir)
                return url, filename, None
            except Exception as e:
                return url, None, str(e)
        
        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            future_to_url = {executor.submit(download_single, url): url for url in image_urls}
            
            for future in as_completed(future_to_url):
                url, filename, error = future.result()
                if error is None and filename:
                    results[url] = filename
                else:
                    failed_urls.append(url)
                    logger.error(f"批量下载失败 {url}: {error}")
        
        if failed_urls:
            logger.warning(f"批量下载完成，{len(failed_urls)} 张图片下载失败")
        else:
            logger.info(f"✅ 批量下载全部成功，共 {len(results)} 张图片")
        
        return results
    
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
    
    def close(self):
        """关闭HTTP客户端"""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __del__(self):
        """析构函数，确保资源清理"""
        self.close()



# 创建全局服务实例
image_service = ImageService()
