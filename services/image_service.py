"""
图片处理服务
"""
import os
import time
import requests
import urllib.parse
from pathlib import Path
from loguru import logger


class ImageService:
    """图片处理服务类"""
    
    def __init__(self):
        # ComfyUI的input目录路径
        self.comfyui_input_dir = Path("/workspace/ComfyUI/input")
    
    def download_image(self, image_url, target_dir=None):
        """
        下载图片到指定目录
        
        Args:
            image_url (str): 图片URL
            target_dir (Path, optional): 目标目录，默认使用ComfyUI input目录
            
        Returns:
            str: 下载后的本地文件名
        """
        if target_dir is None:
            target_dir = self.comfyui_input_dir
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 解析URL获取文件名
            parsed_url = urllib.parse.urlparse(image_url)
            original_filename = os.path.basename(parsed_url.path)
            
            # 如果没有文件扩展名，默认使用.png
            if not original_filename or '.' not in original_filename:
                original_filename = f"image_{int(time.time())}.png"
            
            # 生成唯一的本地文件名（避免冲突）
            timestamp = int(time.time() * 1000)  # 毫秒时间戳
            name, ext = os.path.splitext(original_filename)
            local_filename = f"{name}_{timestamp}{ext}"
            local_path = target_dir / local_filename
            
            logger.debug(f"开始下载图片: {image_url} -> {local_path}")
            
            # 下载图片 - 使用指数退避重试机制
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            max_retries = 3
            base_delay = 1  # 基础延迟1秒
            
            for attempt in range(max_retries + 1):  # 总共尝试4次 (0, 1, 2, 3)
                try:
                    logger.debug(f"尝试下载图片 (第{attempt + 1}次): {image_url}")
                    response = requests.get(image_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    break  # 成功则跳出重试循环
                    
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries:  # 最后一次尝试失败
                        logger.error(f"❌ 下载失败，已达到最大重试次数 ({max_retries + 1}): {str(e)}")
                        raise
                    
                    # 计算退避延迟时间：1秒 → 2秒 → 4秒
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ 下载失败 (第{attempt + 1}次)，{delay}秒后重试: {str(e)}")
                    time.sleep(delay)
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"警告：下载的文件可能不是图片，Content-Type: {content_type}")
            
            # 保存文件
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            logger.info(f"✅ 图片下载成功: {local_filename}, 大小: {file_size} bytes")
            
            return local_filename
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ 下载图片时发生异常: {str(e)}")
            raise
    
    def download_images_batch(self, image_urls, target_dir=None):
        """
        批量下载图片
        
        Args:
            image_urls (list): 图片URL列表
            target_dir (Path, optional): 目标目录，默认使用ComfyUI input目录
            
        Returns:
            dict: {原始URL: 本地文件名} 的映射
        """
        if target_dir is None:
            target_dir = self.comfyui_input_dir
            
        results = {}
        failed_urls = []
        
        logger.info(f"开始批量下载 {len(image_urls)} 张图片")
        
        for i, url in enumerate(image_urls, 1):
            try:
                logger.info(f"下载进度: {i}/{len(image_urls)} - {url}")
                local_filename = self.download_image(url, target_dir)
                results[url] = local_filename
            except Exception as e:
                logger.error(f"下载失败 {url}: {str(e)}")
                failed_urls.append(url)
        
        if failed_urls:
            logger.warning(f"批量下载完成，{len(failed_urls)} 张图片下载失败: {failed_urls}")
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


# 创建全局服务实例
image_service = ImageService()
