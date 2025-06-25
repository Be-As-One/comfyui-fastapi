"""
存储模块 - 统一导出所有存储相关类和函数，保持向后兼容性
"""
from .base import StorageProvider
from .manager import (
    StorageManager,
    create_storage_manager,
    get_storage_manager,
    set_storage_manager,
    initialize_storage,
    upload_binary_image
)
from .providers import (
    GCSProvider,
    CloudflareR2Provider,
    CloudflareImagesProvider
)

__all__ = [
    # 基类
    'StorageProvider',
    
    # 管理器和工具函数
    'StorageManager',
    'create_storage_manager',
    'get_storage_manager',
    'set_storage_manager',
    'initialize_storage',
    'upload_binary_image',
    
    # 存储提供商
    'GCSProvider',
    'CloudflareR2Provider',
    'CloudflareImagesProvider',
]