"""
故障模块：在组装阶段故意崩溃。

微内核应当隔离该模块，并继续加载 user_module 和 order_module。
"""

from paas_core import Service


@Service
class FaultyService:
    def __init__(self):
        raise RuntimeError("故意制造的故障服务崩溃，用于测试隔离机制")


class FaultyController:
    pass
