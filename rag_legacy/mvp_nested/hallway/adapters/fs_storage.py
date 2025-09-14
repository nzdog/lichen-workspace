"""
Filesystem storage adapter.
"""

import json
import os
from pathlib import Path
from typing import Any

from ..ports import Storage
from ..errors import PortError


class FilesystemStorage(Storage):
    """Filesystem-based storage implementation."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def put_json(self, bucket: str, key: str, obj: Any) -> None:
        """Store a JSON object to filesystem."""
        try:
            bucket_path = self.base_path / bucket
            bucket_path.mkdir(parents=True, exist_ok=True)

            file_path = bucket_path / f"{key}.json"
            with open(file_path, 'w') as f:
                json.dump(obj, f, indent=2)
        except Exception as e:
            raise PortError(f"Failed to store {bucket}/{key}: {e}", "filesystem_storage")

    async def get_json(self, bucket: str, key: str) -> Any:
        """Retrieve a JSON object from filesystem."""
        try:
            file_path = self.base_path / bucket / f"{key}.json"
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise PortError(f"Object not found: {bucket}/{key}", "filesystem_storage")
        except Exception as e:
            raise PortError(f"Failed to retrieve {bucket}/{key}: {e}", "filesystem_storage")

    async def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists."""
        file_path = self.base_path / bucket / f"{key}.json"
        return file_path.exists()
