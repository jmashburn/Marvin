"""Base storage provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class StorageMetadata:
    """Metadata about a stored file."""

    storage_key: str
    """Logical key for the file in storage."""
    size: int
    """File size in bytes."""
    content_type: str
    """MIME type of the file."""
    checksum: str | None = None
    """Optional checksum (e.g. MD5, SHA-256)."""
    metadata: dict | None = None
    """Optional custom metadata."""


class BaseStorageProvider(ABC):
    """
    Abstract base class for storage providers.

    Implementations handle actual file storage (local filesystem, S3, etc.)
    while providing a consistent interface for the application.
    """

    @abstractmethod
    def put(
        self,
        storage_key: str,
        file_data: BinaryIO,
        content_type: str,
        metadata: dict | None = None,
    ) -> StorageMetadata:
        """
        Store a file.

        Args:
            storage_key: Logical key for the file (e.g. workspace/assets/2026/07/uuid-file.jpg)
            file_data: Binary file data to store
            content_type: MIME type of the file
            metadata: Optional custom metadata to store with the file

        Returns:
            StorageMetadata with information about the stored file

        Raises:
            Exception: If storage fails
        """
        pass

    @abstractmethod
    def get(self, storage_key: str) -> BinaryIO:
        """
        Retrieve a file.

        Args:
            storage_key: Logical key for the file

        Returns:
            Binary file data

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If retrieval fails
        """
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """
        Delete a file.

        Args:
            storage_key: Logical key for the file

        Returns:
            True if file was deleted, False if it didn't exist

        Raises:
            Exception: If deletion fails
        """
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """
        Check if a file exists.

        Args:
            storage_key: Logical key for the file

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_public_url(self, storage_key: str) -> str:
        """
        Get public URL for accessing a file.

        Args:
            storage_key: Logical key for the file

        Returns:
            Public URL (e.g. /uploads/path or https://cdn.example.com/path)
        """
        pass

    @abstractmethod
    def get_metadata(self, storage_key: str) -> StorageMetadata:
        """
        Get metadata about a stored file.

        Args:
            storage_key: Logical key for the file

        Returns:
            StorageMetadata

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If metadata retrieval fails
        """
        pass
