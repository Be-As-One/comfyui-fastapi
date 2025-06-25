"""
Cloudflare Images 存储提供商
"""
import os
from loguru import logger
from ..base import StorageProvider


class CloudflareImagesProvider(StorageProvider):
    """Cloudflare Images 存储提供商"""

    def __init__(self, account_id: str, api_token: str, delivery_domain: str = None):
        try:
            import requests
            self.account_id = account_id
            self.api_token = api_token
            self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1"
            self.delivery_domain = delivery_domain or f"https://imagedelivery.net/{account_id}"
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {api_token}",
                "User-Agent": "ComfyUI-FastAPI/1.0"
            })
        except ImportError:
            raise ImportError("requests is required for Cloudflare Images provider")

    def _get_image_url(self, image_id: str, variant: str = "public") -> str:
        """获取图片的访问URL"""
        return f"{self.delivery_domain}/{image_id}/{variant}"

    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """上传文件到Cloudflare Images"""
        try:
            with open(source_file_name, 'rb') as f:
                return self._upload_with_file_data(f.read(), destination_path, source_file_name)
        except Exception as e:
            logger.error(f"Failed to upload file to Cloudflare Images: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str) -> str:
        """上传二进制数据到Cloudflare Images"""
        logger.info(f"开始上传二进制数据到Cloudflare Images: {destination_path}")
        logger.debug(f"数据大小: {len(binary_data)} bytes")

        return self._upload_with_file_data(binary_data, destination_path)

    def upload_base64(self, base64_data: str, destination_path: str) -> str:
        """上传base64数据到Cloudflare Images"""
        try:
            import base64
            file_data = base64.b64decode(base64_data)
            return self.upload_binary(file_data, destination_path)
        except Exception as e:
            logger.error(f"Failed to upload base64 data to Cloudflare Images: {e}")
            raise

    def _upload_with_file_data(self, file_data: bytes, destination_path: str, source_file_name: str = None) -> str:
        """内部方法：使用文件数据上传到Cloudflare Images"""
        try:
            filename = os.path.splitext(os.path.basename(destination_path))[0]

            files = {
                'file': ('image.jpg', file_data, 'image/jpeg')
            }
            data = {
                'id': filename,
                'metadata': '{}',
                'requireSignedURLs': 'false'
            }

            logger.debug(f"上传文件到Cloudflare Images，ID: {filename}")
            response = self.session.post(self.base_url, files=files, data=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_id = result['result']['id']
                    url = self._get_image_url(image_id)
                    logger.info(f"Cloudflare Images上传成功: {url}")

                    if source_file_name and os.path.exists(source_file_name):
                        os.remove(source_file_name)
                        logger.info(f"Local file {source_file_name} deleted after upload")

                    return url
                else:
                    error_msg = result.get('errors', [{'message': 'Unknown error'}])[0]['message']
                    raise Exception(f"Cloudflare Images API error: {error_msg}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Cloudflare Images上传失败: {str(e)}")
            logger.error(f"失败详情 - 路径: {destination_path}, 数据大小: {len(file_data)} bytes")
            raise