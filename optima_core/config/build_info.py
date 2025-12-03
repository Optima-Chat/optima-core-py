"""构建信息"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BuildInfo:
    """从环境变量读取的构建信息"""

    git_commit: str = field(default_factory=lambda: os.getenv("GIT_COMMIT", "unknown"))
    git_branch: str = field(default_factory=lambda: os.getenv("GIT_BRANCH", "unknown"))
    build_date: str = field(default_factory=lambda: os.getenv("BUILD_DATE", "unknown"))
    version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "0.1.0"))

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "build_date": self.build_date,
            "version": self.version,
        }

    @property
    def short_commit(self) -> str:
        """返回短 commit hash"""
        if self.git_commit and self.git_commit != "unknown":
            return self.git_commit[:7]
        return "unknown"
