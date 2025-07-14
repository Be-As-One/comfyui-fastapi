"""
统一的媒体文件处理服务

提供图片、音频等多种媒体类型的统一处理接口
"""
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
from loguru import logger
from services.image_service import image_service


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    AUDIO = "audio"
    UNKNOWN = "unknown"


class MediaService:
    """统一的媒体处理服务"""
    
    # 文件扩展名到媒体类型的映射
    FILE_TYPE_MAPPING = {
        # 图片格式
        '.jpg': MediaType.IMAGE,
        '.jpeg': MediaType.IMAGE,
        '.png': MediaType.IMAGE,
        '.gif': MediaType.IMAGE,
        '.bmp': MediaType.IMAGE,
        '.webp': MediaType.IMAGE,
        '.svg': MediaType.IMAGE,
        '.tiff': MediaType.IMAGE,
        '.tif': MediaType.IMAGE,
        # 音频格式
        '.mp3': MediaType.AUDIO,
        '.wav': MediaType.AUDIO,
        '.ogg': MediaType.AUDIO,
        '.flac': MediaType.AUDIO,
        '.aac': MediaType.AUDIO,
        '.m4a': MediaType.AUDIO,
        '.wma': MediaType.AUDIO,
    }
    
    def __init__(self):
        self.image_service = image_service
    
    def detect_media_type(self, url: str) -> MediaType:
        """
        检测URL指向的媒体类型
        
        Args:
            url (str): 媒体文件URL
            
        Returns:
            MediaType: 检测到的媒体类型
        """
        try:
            # 从URL中提取文件扩展名
            path = Path(url.split('?')[0])  # 移除查询参数
            ext = path.suffix.lower()
            
            return self.FILE_TYPE_MAPPING.get(ext, MediaType.UNKNOWN)
        except Exception as e:
            logger.warning(f"检测媒体类型失败: {url}, 错误: {str(e)}")
            return MediaType.UNKNOWN
    
    def is_remote_url(self, url: str) -> bool:
        """检查是否为远程URL"""
        if not isinstance(url, str):
            return False
        return url.startswith("http://") or url.startswith("https://")
    
    def download_media(self, media_url: str, media_type: Optional[MediaType] = None) -> str:
        """
        下载媒体文件
        
        Args:
            media_url (str): 媒体文件URL
            media_type (MediaType, optional): 媒体类型，如果未指定则自动检测
            
        Returns:
            str: 下载后的本地文件名
        """
        # 自动检测媒体类型
        if media_type is None:
            media_type = self.detect_media_type(media_url)
        
        # 所有类型都使用相同的下载逻辑
        # image_service 已经支持下载任何类型的文件
        if media_type == MediaType.AUDIO:
            logger.info(f"下载音频文件: {media_url}")
        elif media_type == MediaType.IMAGE:
            logger.info(f"下载图片文件: {media_url}")
        else:
            logger.warning(f"未知媒体类型，将作为通用文件下载: {media_url}")
            
        return self.image_service.download_image(media_url)
    
    def download_media_batch_sync(self, media_urls: List[str]) -> Dict[str, str]:
        """
        批量下载媒体文件（同步版本）
        
        Args:
            media_urls (List[str]): 媒体文件URL列表
            
        Returns:
            Dict[str, str]: {url: local_filename} 的映射
        """
        # 记录不同类型的文件数量用于日志
        media_types_count = {}
        for url in media_urls:
            media_type = self.detect_media_type(url)
            media_types_count[media_type] = media_types_count.get(media_type, 0) + 1
        
        # 输出日志
        for media_type, count in media_types_count.items():
            logger.info(f"发现 {count} 个 {media_type.value} 文件")
        
        # 使用 image_service 的批量下载功能
        # 它已经支持下载任何类型的文件
        logger.info(f"开始批量下载 {len(media_urls)} 个文件")
        return self.image_service.download_images_batch(media_urls)
    
    def validate_media_file(self, file_path: str, expected_type: MediaType) -> bool:
        """
        验证媒体文件是否符合预期类型
        
        Args:
            file_path (str): 文件路径
            expected_type (MediaType): 预期的媒体类型
            
        Returns:
            bool: 是否符合预期类型
        """
        try:
            ext = Path(file_path).suffix.lower()
            actual_type = self.FILE_TYPE_MAPPING.get(ext, MediaType.UNKNOWN)
            
            if actual_type != expected_type:
                logger.warning(f"文件类型不匹配: {file_path}, 预期: {expected_type.value}, 实际: {actual_type.value}")
                return False
            
            # 检查文件是否存在
            if not Path(file_path).exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证媒体文件失败: {file_path}, 错误: {str(e)}")
            return False


# 全局媒体服务实例
media_service = MediaService()