"""
Google Cloud Storage 存储提供商
"""
import os
from io import BytesIO
from loguru import logger
from ..base import StorageProvider


class GCSProvider(StorageProvider):
    """Google Cloud Storage 提供商"""

    def __init__(self, bucket_name: str, cdn_url: str = None):
        try:
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            self.bucket_name = bucket_name
            self.cdn_url = cdn_url
        except ImportError:
            raise ImportError("google-cloud-storage is required for GCS provider")

    def _get_cdn_url(self, destination_path: str) -> str:
        """获取CDN URL，如果CDN未配置则降级使用直连URL"""
        if self.cdn_url:
            # 确保CDN URL不以/结尾，destination_path不以/开头
            cdn_base = self.cdn_url.rstrip('/')
            path = destination_path.lstrip('/')
            url = f"{cdn_base}/{path}"
            logger.debug(f"使用CDN URL: {url}")
            return url
        else:
            # 降级使用直连URL
            url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_path}"
            logger.debug(f"CDN未配置，使用直连URL: {url}")
            return url

    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """上传文件到GCS - 自动支持大文件分块上传"""
        try:
            blob = self.bucket.blob(destination_path)
            
            # 获取文件大小
            file_size = os.path.getsize(source_file_name)
            logger.info(f"准备上传文件: {source_file_name} ({file_size / 1024 / 1024:.2f}MB)")
            
            # 对于大文件，设置合适的分块大小
            if file_size > 100 * 1024 * 1024:  # > 100MB
                # 根据文件大小动态设置分块大小
                if file_size > 1024 * 1024 * 1024:  # > 1GB
                    blob.chunk_size = 256 * 1024 * 1024  # 256MB chunks
                    logger.info(f"大文件检测: 使用 256MB 分块上传")
                else:
                    blob.chunk_size = 64 * 1024 * 1024  # 64MB chunks
                    logger.info(f"中等文件检测: 使用 64MB 分块上传")
            
            # SDK 会自动处理分块上传和 resumable upload
            blob.upload_from_filename(source_file_name)
            logger.info(f"File {source_file_name} uploaded to GCS: {destination_path}")

            os.remove(source_file_name)
            logger.info(f"Local file {source_file_name} deleted after upload")

            return self._get_cdn_url(destination_path)
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str, content_type: str = None) -> str:
        """上传二进制数据到GCS - 支持大数据分块上传"""
        data_size = len(binary_data)
        logger.info(f"开始上传二进制数据到GCS: {destination_path}")
        logger.info(f"数据大小: {data_size / 1024 / 1024:.2f}MB")

        try:
            # 根据文件扩展名推断 Content-Type
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(destination_path)
                if not content_type:
                    content_type = 'application/octet-stream'

            logger.debug(f"Content-Type: {content_type}")

            blob = self.bucket.blob(destination_path)

            # 对于大数据，设置分块大小
            if data_size > 100 * 1024 * 1024:  # > 100MB
                # 根据数据大小动态设置分块大小
                if data_size > 1024 * 1024 * 1024:  # > 1GB
                    blob.chunk_size = 256 * 1024 * 1024  # 256MB chunks
                    logger.info(f"大数据检测: 使用 256MB 分块上传")
                else:
                    blob.chunk_size = 64 * 1024 * 1024  # 64MB chunks
                    logger.info(f"中等数据检测: 使用 64MB 分块上传")

            # 使用 BytesIO 实现流式上传，避免多次复制数据
            with BytesIO(binary_data) as data_stream:
                blob.upload_from_file(data_stream, size=data_size, content_type=content_type, rewind=True)

            logger.debug(f"数据上传完成")

            url = self._get_cdn_url(destination_path)
            logger.info(f"GCS上传成功: {url}")
            return url
        except Exception as e:
            logger.error(f"GCS上传失败: {str(e)}")
            logger.error(f"失败详情 - 路径: {destination_path}, 数据大小: {data_size / 1024 / 1024:.2f}MB")
            raise

    def upload_base64(self, base64_data: str, destination_path: str) -> str:
        """上传base64数据到GCS"""
        try:
            import base64
            file_data = base64.b64decode(base64_data)
            file_obj = BytesIO(file_data)

            blob = self.bucket.blob(destination_path)
            blob.upload_from_file(file_obj, content_type='application/octet-stream')
            blob.make_public()

            url = self._get_cdn_url(destination_path)
            logger.info(f"Base64 data uploaded to GCS: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload base64 data to GCS: {e}")
            raise