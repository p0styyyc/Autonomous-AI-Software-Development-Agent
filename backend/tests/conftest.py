"""pytest 共享 fixtures"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def workspace():
    """创建临时 workspace 目录"""
    with tempfile.TemporaryDirectory(prefix="test_workspace_") as tmp:
        yield str(Path(tmp).resolve())


@pytest.fixture
def sample_py_file(workspace):
    """在 workspace 中创建一个示例 Python 文件"""
    path = Path(workspace) / "sample.py"
    path.write_text("def hello():\n    return 'world'\n\nprint(hello())\n")
    return str(path)
