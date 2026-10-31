"""业务异常：由 repository 抛出，main 中统一转换为 HTTP 响应。"""

from __future__ import annotations


class RepoError(Exception):
    pass


class NotFound(RepoError):
    pass


class Conflict(RepoError):
    pass


class BadRequest(RepoError):
    pass
