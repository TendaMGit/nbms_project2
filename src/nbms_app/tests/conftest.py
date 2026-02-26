import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest


if os.name == "nt" and sys.version_info >= (3, 13):
    @pytest.fixture
    def tmp_path():
        """Work around pytest tmp_path ACL failures seen on some Windows 3.13 setups."""
        root = Path(__file__).resolve().parents[3] / ".pytest_tmp_local"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"nbms-pytest-{uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)
