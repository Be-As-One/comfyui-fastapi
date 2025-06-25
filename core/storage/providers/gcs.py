"""
Google Cloud Storage 存储提供商
"""
import os
from io import BytesIO
from loguru import logger
from ..base import StorageProvider


class GCSProvider(StorageProvider):
    """Google Cloud Storage 提供商"""

    def __init__(self, bucket_name: str):
        try:
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            self.bucket_name = bucket_name
        except ImportError:
            raise ImportError("google-cloud-storage is required for GCS provider")

    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """上传文件到GCS"""
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(source_file_name)
            logger.info(f"File {source_file_name} uploaded to GCS: {destination_path}")

            os.remove(source_file_name)
            logger.info(f"Local file {source_file_name} deleted after upload")

            return f"https://storage.googleapis.com/{self.bucket_name}/{destination_path}"
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str) -> str:
        """上传二进制数据到GCS"""
        logger.info(f"开始上传二进制数据到GCS: {destination_path}")
        logger.debug(f"数据大小: {len(binary_data)} bytes")

        try:
            blob = self.bucket.blob(destination_path)
            logger.debug(f"创建GCS blob对象: {destination_path}")

            blob.upload_from_string(binary_data)
            logger.debug(f"数据上传完成")

            url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_path}"
            logger.info(f"GCS上传成功: {url}")
            return url
        except Exception as e:
            logger.error(f"GCS上传失败: {str(e)}")
            logger.error(f"失败详情 - 路径: {destination_path}, 数据大小: {len(binary_data)} bytes")
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

            url = blob.public_url
            logger.info(f"Base64 data uploaded to GCS: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload base64 data to GCS: {e}")
            raise