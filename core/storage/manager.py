"""
存储管理器 - 统一管理多种存储提供商
"""
import os
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from config.settings import (
    bucket_name,
    storage_provider as default_storage_provider,
    r2_bucket_name,
    r2_account_id,
    r2_access_key,
    r2_secret_key,
    r2_public_domain,
    cf_images_account_id,
    cf_images_api_token,
    cf_images_delivery_domain
)
from .base import StorageProvider


class StorageManager:
    """存储管理器 - 统一管理多种存储提供商"""

    def __init__(self, auto_configure: bool = True):
        self.providers = {}
        self.default_provider = None
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 自动根据环境变量配置存储提供商
        if auto_configure:
            self._auto_configure()

    def _auto_configure(self):
        """根据环境变量自动配置存储提供商"""
        logger.debug(f"自动配置存储提供商: {default_storage_provider}")

        # 根据配置的提供商类型进行配置
        if default_storage_provider == 'r2':
            self._configure_r2()
        elif default_storage_provider == 'gcs':
            self._configure_gcs()
        elif default_storage_provider == 'cf_images':
            self._configure_cf_images()

        if self.providers:
            logger.info(f"存储管理器已配置: {list(self.providers.keys())}, 默认: {self.default_provider}")
        else:
            logger.warning("未配置任何存储提供商，文件上传将不可用")

    def _configure_r2(self):
        """配置Cloudflare R2提供商"""
        if not all([r2_bucket_name, r2_account_id, r2_access_key, r2_secret_key]):
            logger.warning(f"R2配置不完整: bucket={bool(r2_bucket_name)}, account={bool(r2_account_id)}, access_key={bool(r2_access_key)}, secret_key={bool(r2_secret_key)}")
            return

        try:
            from .providers.cloudflare_r2 import CloudflareR2Provider
            r2_provider = CloudflareR2Provider(
                bucket_name=r2_bucket_name,
                account_id=r2_account_id,
                access_key=r2_access_key,
                secret_key=r2_secret_key,
                public_domain=r2_public_domain
            )
            self.register_provider('r2', r2_provider, is_default=True)
            logger.info("✅ Cloudflare R2 provider configured")
        except ImportError:
            logger.warning("boto3 未安装，跳过 R2 配置")
        except Exception as e:
            logger.error(f"配置 R2 失败: {e}")

    def _configure_gcs(self):
        """配置GCS提供商"""
        if not bucket_name:
            logger.warning("GCS bucket 未配置")
            return

        try:
            from .providers.gcs import GCSProvider
            from config.settings import cdn_url
            gcs_provider = GCSProvider(bucket_name, cdn_url=cdn_url)
            self.register_provider('gcs', gcs_provider, is_default=True)
            logger.info("✅ GCS provider configured")
        except ImportError:
            logger.warning("google-cloud-storage 未安装，跳过 GCS 配置")
        except Exception as e:
            logger.error(f"配置 GCS 失败: {e}")

    def _configure_cf_images(self):
        """配置Cloudflare Images提供商"""
        if not all([cf_images_account_id, cf_images_api_token]):
            logger.warning("Cloudflare Images 配置不完整")
            return

        try:
            from .providers.cloudflare_images import CloudflareImagesProvider
            cf_images_provider = CloudflareImagesProvider(
                account_id=cf_images_account_id,
                api_token=cf_images_api_token,
                delivery_domain=cf_images_delivery_domain
            )
            self.register_provider('cf_images', cf_images_provider, is_default=True)
            logger.info("✅ Cloudflare Images provider configured")
        except ImportError:
            logger.warning("requests 未安装，跳过 Cloudflare Images 配置")
        except Exception as e:
            logger.error(f"配置 Cloudflare Images 失败: {e}")

    def register_provider(self, name: str, provider: StorageProvider, is_default: bool = False):
        """注册存储提供商"""
        self.providers[name] = provider
        if is_default or self.default_provider is None:
            self.default_provider = name

    def get_provider(self, name: str = None) -> StorageProvider:
        """获取存储提供商"""
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"存储提供商 '{provider_name}' 未找到，可用: {list(self.providers.keys())}")
        return self.providers[provider_name]

    def upload_file(self, source_file_name: str, destination_path: str, provider: str = None) -> str:
        """上传文件"""
        return self.get_provider(provider).upload_file(source_file_name, destination_path)

    def upload_binary(self, binary_data: bytes, destination_path: str, provider: str = None) -> str:
        """上传二进制数据"""
        return self.get_provider(provider).upload_binary(binary_data, destination_path)

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

    def is_initialized(self) -> bool:
        """检查存储管理器是否已配置（向后兼容）"""
        return bool(self.providers)

    def initialize(self):
        """初始化存储管理器（向后兼容，现在是空操作）"""
        # 已在 __init__ 中自动配置，这里保留用于向后兼容
        if not self.providers:
            self._auto_configure()


# 全局存储管理器实例（懒加载）
_global_storage_manager = None


def get_storage_manager() -> StorageManager:
    """获取全局存储管理器实例"""
    global _global_storage_manager
    if _global_storage_manager is None:
        _global_storage_manager = StorageManager()
    return _global_storage_manager


def set_storage_manager(manager: StorageManager):
    """设置全局存储管理器实例"""
    global _global_storage_manager
    _global_storage_manager = manager


def initialize_storage():
    """初始化全局存储管理器（向后兼容）"""
    return get_storage_manager()


def upload_binary_image(binary_data: bytes, destination_path: str) -> str:
    """向后兼容：上传二进制图片"""
    return get_storage_manager().upload_binary(binary_data, destination_path)
