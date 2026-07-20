"""
PaaS 核心：模块化微内核 PaaS 的稳定内核。

本包由人类架构师维护，AI 智能体禁止修改。
"""

from .sdk import (
    Controller,
    DELETE,
    GET,
    Inject,
    Mapper,
    PATCH,
    POST,
    PUT,
    Service,
    get_meta,
    is_component,
)

__all__ = [
    "Controller",
    "Service",
    "Mapper",
    "Inject",
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "get_meta",
    "is_component",
]
