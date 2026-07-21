"""
审查部署智能体
==============

校验生成代码、安全写入 plugins/ 沙箱、执行静态检查并重载内核。
"""

from __future__ import annotations

from typing import Any, Dict, List

from paas_core.kernel.microkernel import MicroKernel
from paas_core.server.route_bridge import summarize_report

from .. import agent_tools
from ..locks import plugin_write_lock
from ..schemas import PipelineState


def _validate_files(files: Dict[str, str]) -> List[str]:
    """轻量级格式校验，返回问题列表。"""
    issues: List[str] = []
    mapper_file = next((f for f in files if f.endswith("Mapper.py")), None)
    service_file = next((f for f in files if f.endswith("Service.py")), None)
    controller_file = next((f for f in files if f.endswith("Controller.py")), None)

    if not mapper_file:
        issues.append("缺少 Mapper 文件")
    if not service_file:
        issues.append("缺少 Service 文件")
    if not controller_file:
        issues.append("缺少 Controller 文件")

    if controller_file and "@Controller" not in files[controller_file]:
        issues.append("Controller 缺少 @Controller 装饰器")
    if service_file and "@Service" not in files[service_file]:
        issues.append("Service 缺少 @Service 装饰器")
    if mapper_file and "@Mapper" not in files[mapper_file]:
        issues.append("Mapper 缺少 @Mapper 装饰器")

    return issues


def run_reviewer_deployer_node(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """
    LangGraph 流水线中的审查与部署节点。

    将 state.files 写入沙箱，执行静态检查，并重载内核。
    """
    logs = list(state.get("logs", []))
    files = state.get("files", {})
    module_name = state.get("module_name", "")

    if not module_name:
        # 从 architecture_doc 回退
        arch = state.get("architecture_doc")
        if arch:
            module_name = arch.get("module_name", "")
    if not module_name:
        logs.append("模块名缺失，无法部署")
        return {
            "status": "deploy_failed",
            "checks": {},
            "reload_report": {},
            "logs": logs,
        }

    validation_issues = _validate_files(files)
    if validation_issues:
        logs.append(f"格式校验失败: {validation_issues}")
        return {
            "status": "validation_failed",
            "checks": {"format": {"ok": False, "errors": validation_issues}},
            "reload_report": {},
            "logs": logs,
        }

    try:
        with plugin_write_lock():
            agent_tools.create_plugin(module_name)
            logs.append(f"创建插件目录: {module_name}")

            written: List[str] = []
            for file_name, content in files.items():
                try:
                    agent_tools.write_plugin_file(module_name, file_name, content)
                    written.append(file_name)
                except Exception as exc:
                    logs.append(f"写入 {file_name} 失败: {exc}")

            if len(written) != len(files):
                return {
                    "status": "write_failed",
                    "written": written,
                    "checks": {},
                    "reload_report": {},
                    "logs": logs,
                }

            logs.append(f"成功写入文件: {written}")

            checks: Dict[str, Any] = {}
            all_ok = True
            for file_name in files:
                result = agent_tools.static_check(module_name, file_name)
                checks[file_name] = result
                if not result.get("ok"):
                    all_ok = False
                    logs.append(f"静态检查失败 {file_name}: {result.get('errors')}")

            if not all_ok:
                return {
                    "status": "static_check_failed",
                    "written": written,
                    "checks": checks,
                    "reload_report": {},
                    "logs": logs,
                }

            logs.append("静态检查通过")

            report = kernel.reload_plugin(module_name)
            summary = summarize_report(report)
            logs.append(f"内核重载成功: {summary}")
            return {
                "status": "deployed",
                "written": written,
                "checks": checks,
                "reload_report": summary,
                "logs": logs,
            }
    except agent_tools.AgentSandboxError as exc:
        logs.append(f"创建插件目录失败: {exc}")
        return {
            "status": "write_failed",
            "checks": {},
            "reload_report": {},
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"部署失败: {exc}")
        return {
            "status": "reload_failed",
            "written": [],
            "checks": {},
            "reload_report": {"error": str(exc)},
            "logs": logs,
        }
