"""
系统口热重载入ロ。

uvicorn --reload 要求以导入字符串形式提供 app，因此本模块在导入时完成内核启动
并创建 FastAPI 应用。代码变更后 uvicorn 会重新导入本模块，从而用最新代码重建内核与 app。
"""

from paas_core.kernel.microkernel import MicroKernel
from paas_core.server.system.system_server import create_system_app

kernel = MicroKernel()
kernel.boot()
app = create_system_app(kernel)
