"""
Cloudflare R2 存储提供商
"""
import os
from loguru import logger
from ..base import StorageProvider


class CloudflareR2Provider(StorageProvider):
    """Cloudflare R2 存储提供商"""

    def __init__(self, bucket_name: str, account_id: str, access_key: str, secret_key: str, public_domain: str = None):
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'
            )
            self.bucket_name = bucket_name
            self.public_domain = public_domain or f"https://pub-{account_id}.r2.dev"
        except ImportError:
            raise ImportError("boto3 is required for Cloudflare R2 provider")

    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """上传文件到Cloudflare R2"""
        try:
            self.s3_client.upload_file(source_file_name, self.bucket_name, destination_path)
            logger.info(f"File {source_file_name} uploaded to R2: {destination_path}")

            os.remove(source_file_name)
            logger.info(f"Local file {source_file_name} deleted after upload")

            return f"{self.public_domain}/{destination_path}"
        except Exception as e:
            logger.error(f"Failed to upload file to R2: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str, content_type: str = None) -> str:
        """上传二进制数据到Cloudflare R2"""
        logger.info(f"开始上传二进制数据到R2: {destination_path}")
        logger.debug(f"数据大小: {len(binary_data)} bytes")

        try:
            # 根据文件扩展名推断 Content-Type
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(destination_path)
                if not content_type:
                    content_type = 'application/octet-stream'

            logger.debug(f"Content-Type: {content_type}")

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=destination_path,
                Body=binary_data,
                ContentType=content_type
            )
            logger.debug(f"R2上传完成")

            url = f"{self.public_domain}/{destination_path}"
            logger.info(f"R2上传成功: {url}")
            return url
        except Exception as e:
            logger.error(f"R2上传失败: {str(e)}")
            logger.error(f"失败详情 - 路径: {destination_path}, 数据大小: {len(binary_data)} bytes")
            raise

    def upload_base64(self, base64_data: str, destination_path: str) -> str:
        """上传base64数据到Cloudflare R2"""
        try:
            import base64
            file_data = base64.b64decode(base64_data)
            return self.upload_binary(file_data, destination_path)
        except Exception as e:
            logger.error(f"Failed to upload base64 data to R2: {e}")
            raise