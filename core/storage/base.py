"""
存储提供商抽象基类
"""
from abc import ABC, abstractmethod


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