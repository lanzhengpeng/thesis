"""
PaaS 核心：模块化微内核 PaaS 的稳定内核。

本包由人类架构师维护，AI 智能体禁止修改。

对外导出的装饰器与辅助函数是 AI 编写业务插件时允许使用的唯一内核契约。
"""

# 从 SDK 模块导出装饰器与元数据辅助函数，供业务插件导入使用。
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
    # 组件装饰器
    "Controller",
    "Service",
    "Mapper",
    # 注入装饰器
    "Inject",
    # HTTP 方法装饰器
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    # 元数据辅助函数
    "get_meta",
    "is_component",
]
