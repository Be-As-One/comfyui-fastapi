"""
存储工具 - 支持多种云存储提供商
"""
import os
import base64
from abc import ABC, abstractmethod
from io import BytesIO
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from config.settings import bucket_name

class StorageProvider(ABC):
    """存储提供商抽象基类"""

    @abstractmethod
    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """上传文件，返回URL"""
        pass

    @abstractmethod
    def upload_binary(self, binary_data: bytes, destination_path: str) -> str:
        """上传二进制数据，返回URL"""
        pass

    @abstractmethod
    def upload_base64(self, base64_data: str, destination_path: str) -> str:
        """上传base64数据，返回URL"""
        pass

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

            # 删除本地文件
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

            # 删除本地文件
            os.remove(source_file_name)
            logger.info(f"Local file {source_file_name} deleted after upload")

            return f"{self.public_domain}/{destination_path}"
        except Exception as e:
            logger.error(f"Failed to upload file to R2: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str) -> str:
        """上传二进制数据到Cloudflare R2"""
        logger.info(f"开始上传二进制数据到R2: {destination_path}")
        logger.debug(f"数据大小: {len(binary_data)} bytes")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=destination_path,
                Body=binary_data
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
            file_data = base64.b64decode(base64_data)
            return self.upload_binary(file_data, destination_path)
        except Exception as e:
            logger.error(f"Failed to upload base64 data to R2: {e}")
            raise

class StorageManager:
    """存储管理器 - 统一管理多种存储提供商"""

    def __init__(self):
        self.providers = {}
        self.default_provider = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False

    def register_provider(self, name: str, provider: StorageProvider, is_default: bool = False):
        """注册存储提供商"""
        self.providers[name] = provider
        if is_default or self.default_provider is None:
            self.default_provider = name
        logger.info(f"📦 注册存储提供商: {name}")

    def get_provider(self, name: str = None) -> StorageProvider:
        """获取存储提供商"""
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Storage provider '{provider_name}' not found")
        return self.providers[provider_name]

    def upload_file(self, source_file_name: str, destination_path: str, provider: str = None) -> str:
        """上传文件"""
        return self.get_provider(provider).upload_file(source_file_name, destination_path)

    def upload_binary(self, binary_data: bytes, destination_path: str, provider: str = None) -> str:
        """上传二进制数据"""
        # 检查是否已初始化
        if not self.is_initialized():
            raise RuntimeError("存储管理器未初始化，请先调用 initialize() 方法")

        provider_name = provider or self.default_provider
        logger.info(f"使用存储提供商上传: {provider_name}")
        logger.debug(f"上传路径: {destination_path}, 数据大小: {len(binary_data)} bytes")

        try:
            result = self.get_provider(provider).upload_binary(binary_data, destination_path)
            logger.info(f"存储管理器上传成功: {result}")
            return result
        except Exception as e:
            logger.error(f"存储管理器上传失败: {str(e)}")
            logger.error(f"提供商: {provider_name}, 路径: {destination_path}")
            raise

    def upload_base64(self, base64_data: str, destination_path: str, provider: str = None) -> str:
        """上传base64数据"""
        return self.get_provider(provider).upload_base64(base64_data, destination_path)

    def upload_file_async(self, source_file_name: str, destination_path: str, provider: str = None):
        """异步上传文件"""
        future = self.executor.submit(self.upload_file, source_file_name, destination_path, provider)
        return future

    def upload_binary_async(self, binary_data: bytes, destination_path: str, provider: str = None):
        """异步上传二进制数据"""
        future = self.executor.submit(self.upload_binary, binary_data, destination_path, provider)
        return future

    def initialize(self):
        """初始化存储管理器，配置所有可用的存储提供商"""
        if self._initialized:
            logger.debug("存储管理器已经初始化，跳过")
            return

        logger.info("🔧 开始初始化存储管理器...")

        # 清空现有提供商
        self.providers.clear()
        self.default_provider = None

        # 从环境变量获取配置
        storage_provider = os.getenv('STORAGE_PROVIDER', 'gcs')
        logger.debug(f"配置的存储提供商: {storage_provider}")

        # 尝试配置GCS
        if storage_provider == 'gcs' or os.getenv('GCS_BUCKET_NAME'):
            try:
                gcs_bucket = os.getenv('GCS_BUCKET_NAME', bucket_name)
                if gcs_bucket:
                    logger.debug(f"配置 GCS bucket: {gcs_bucket}")
                    gcs_provider = GCSProvider(gcs_bucket)
                    self.register_provider('gcs', gcs_provider, is_default=(storage_provider == 'gcs'))
                    logger.info("✅ GCS provider configured")
            except ImportError:
                logger.warning("⚠️ google-cloud-storage not installed, skipping GCS provider")
            except Exception as e:
                logger.warning(f"⚠️ Failed to configure GCS provider: {e}")

        # 尝试配置Cloudflare R2
        if storage_provider == 'r2' or os.getenv('R2_BUCKET_NAME'):
            try:
                r2_bucket = os.getenv('R2_BUCKET_NAME')
                r2_account_id = os.getenv('R2_ACCOUNT_ID')
                r2_access_key = os.getenv('R2_ACCESS_KEY')
                r2_secret_key = os.getenv('R2_SECRET_KEY')
                r2_public_domain = os.getenv('R2_PUBLIC_DOMAIN')

                if all([r2_bucket, r2_account_id, r2_access_key, r2_secret_key]):
                    logger.debug(f"配置 R2 bucket: {r2_bucket}")
                    r2_provider = CloudflareR2Provider(
                        bucket_name=r2_bucket,
                        account_id=r2_account_id,
                        access_key=r2_access_key,
                        secret_key=r2_secret_key,
                        public_domain=r2_public_domain
                    )
                    self.register_provider('r2', r2_provider, is_default=(storage_provider == 'r2'))
                    logger.info("✅ Cloudflare R2 provider configured")
                else:
                    logger.warning("⚠️ R2 configuration incomplete, skipping R2 provider")
            except ImportError:
                logger.warning("⚠️ boto3 not installed, skipping R2 provider")
            except Exception as e:
                logger.warning(f"⚠️ Failed to configure R2 provider: {e}")

        if not self.providers:
            logger.warning("⚠️ No storage providers configured, file uploads will be disabled")
        else:
            logger.info(f"📦 Storage manager initialized with providers: {list(self.providers.keys())}")
            logger.info(f"📦 Default provider: {self.default_provider}")

        self._initialized = True
        logger.info("✅ 存储管理器初始化完成")

    def is_initialized(self) -> bool:
        """检查存储管理器是否已初始化"""
        return self._initialized and bool(self.providers)

def create_storage_manager() -> StorageManager:
    """创建并配置存储管理器"""
    manager = StorageManager()

    # 从环境变量获取配置
    storage_provider = os.getenv('STORAGE_PROVIDER', 'gcs')

    # 尝试配置GCS
    if storage_provider == 'gcs' or os.getenv('GCS_BUCKET_NAME'):
        try:
            gcs_bucket = os.getenv('GCS_BUCKET_NAME', bucket_name)
            if gcs_bucket:
                gcs_provider = GCSProvider(gcs_bucket)
                manager.register_provider('gcs', gcs_provider, is_default=(storage_provider == 'gcs'))
                logger.info("✅ GCS provider configured")
        except ImportError:
            logger.warning("⚠️ google-cloud-storage not installed, skipping GCS provider")
        except Exception as e:
            logger.warning(f"⚠️ Failed to configure GCS provider: {e}")

    # 尝试配置Cloudflare R2
    if storage_provider == 'r2' or os.getenv('R2_BUCKET_NAME'):
        try:
            r2_bucket = os.getenv('R2_BUCKET_NAME')
            r2_account_id = os.getenv('R2_ACCOUNT_ID')
            r2_access_key = os.getenv('R2_ACCESS_KEY')
            r2_secret_key = os.getenv('R2_SECRET_KEY')
            r2_public_domain = os.getenv('R2_PUBLIC_DOMAIN')

            if all([r2_bucket, r2_account_id, r2_access_key, r2_secret_key]):
                r2_provider = CloudflareR2Provider(
                    bucket_name=r2_bucket,
                    account_id=r2_account_id,
                    access_key=r2_access_key,
                    secret_key=r2_secret_key,
                    public_domain=r2_public_domain
                )
                manager.register_provider('r2', r2_provider, is_default=(storage_provider == 'r2'))
                logger.info("✅ Cloudflare R2 provider configured")
            else:
                logger.warning("⚠️ R2 configuration incomplete, skipping R2 provider")
        except ImportError:
            logger.warning("⚠️ boto3 not installed, skipping R2 provider")
        except Exception as e:
            logger.warning(f"⚠️ Failed to configure R2 provider: {e}")

    if not manager.providers:
        logger.warning("⚠️ No storage providers configured, file uploads will be disabled")
    else:
        logger.info(f"📦 Storage manager initialized with providers: {list(manager.providers.keys())}")

    return manager

# 全局存储管理器实例变量
_global_storage_manager = None

def get_storage_manager() -> StorageManager:
    """获取全局存储管理器实例"""
    global _global_storage_manager
    if _global_storage_manager is None:
        raise RuntimeError("存储管理器未初始化，请先调用 set_storage_manager() 设置实例")
    return _global_storage_manager

def set_storage_manager(manager: StorageManager):
    """设置全局存储管理器实例"""
    global _global_storage_manager
    _global_storage_manager = manager

def initialize_storage():
    """初始化全局存储管理器"""
    manager = StorageManager()
    manager.initialize()
    set_storage_manager(manager)
    return manager

# 向后兼容的接口
def upload_binary_image(binary_data: bytes, destination_path: str) -> str:
    """向后兼容：上传二进制图片"""
    return get_storage_manager().upload_binary(binary_data, destination_path)
