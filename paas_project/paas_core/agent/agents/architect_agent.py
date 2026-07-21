"""
架构设计智能体
==============

根据需求文档输出模块架构：模块名、API 前缀、类结构、依赖与调用图。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..llm_utils import invoke_json
from ..prompts import ARCHITECT_SYSTEM_PROMPT, architect_prompt
from ..schemas import ArchitectureDoc, PipelineState, RequirementsDoc


def _pluralize(word: str) -> str:
    """极简复数化。"""
    if not word or word.endswith("s"):
        return word
    return f"{word}s"


def _snake_to_camel(name: str) -> str:
    """snake_case 转 CamelCase。"""
    return "".join(part.capitalize() for part in name.split("_") if part)


def _build_architecture_from_requirements(req: RequirementsDoc) -> ArchitectureDoc:
    """当 LLM 不可用时，根据需求文档构造默认架构。"""
    module_name = req.get("module_name", "agent_demo_module")
    entities = req.get("entities") or [{"name": "item", "fields": ["id", "name"]}]
    primary_entity = entities[0].get("name", "item")
    camel = _snake_to_camel(primary_entity)
    prefix = f"/api/{_pluralize(primary_entity.lower())}"

    mapper_class = f"{camel}Mapper"
    service_class = f"{camel}Service"
    controller_class = f"{camel}Controller"

    cross_deps = req.get("cross_module_dependencies") or []
    service_deps = [mapper_class]
    service_deps.extend(_snake_to_camel(d.replace("_module", "")) + "Service" for d in cross_deps)

    endpoints = req.get("api_endpoints") or [
        {"method": "GET", "path": "/", "description": "查询列表"},
        {"method": "GET", "path": "/{id}", "description": "查询详情"},
        {"method": "POST", "path": "/", "description": "创建"},
    ]

    controller_methods: List[Dict[str, Any]] = []
    service_methods: List[Dict[str, Any]] = []
    mapper_methods: List[Dict[str, Any]] = []
    calls_graph: List[Dict[str, str]] = []

    fields = entities[0].get("fields") or ["name"]
    # 去掉 id，作为创建参数
    create_fields = [f for f in fields if f != "id"]

    for ep in endpoints:
        method = ep.get("method", "GET").upper()
        path = ep.get("path", "/")
        desc = ep.get("description", "")

        if method == "GET" and path == "/":
            method_name = f"list_{_pluralize(primary_entity.lower())}"
            controller_methods.append({
                "name": method_name,
                "http_method": "GET",
                "path": "/",
                "calls": [f"{service_class}.{method_name}"],
                "feature": desc or "查询列表",
            })
            service_methods.append({
                "name": method_name,
                "params": [],
                "calls": [f"{mapper_class}.list_all"],
                "feature": desc or "查询列表",
            })
            mapper_methods.append({
                "name": "list_all",
                "params": [],
                "feature": "全量列表",
            })
            calls_graph.append({
                "source": f"{controller_class}.{method_name}",
                "target": f"{service_class}.{method_name}",
            })
            calls_graph.append({
                "source": f"{service_class}.{method_name}",
                "target": f"{mapper_class}.list_all",
            })

        elif method == "GET" and "{id}" in path:
            method_name = f"get_{primary_entity.lower()}"
            controller_methods.append({
                "name": method_name,
                "http_method": "GET",
                "path": "/{id}",
                "calls": [f"{service_class}.{method_name}"],
                "feature": desc or "查询详情",
            })
            service_methods.append({
                "name": method_name,
                "params": [f"{primary_entity.lower()}_id"],
                "calls": [f"{mapper_class}.get"],
                "feature": desc or "查询详情",
            })
            mapper_methods.append({
                "name": "get",
                "params": [f"{primary_entity.lower()}_id"],
                "feature": "根据 ID 查询",
            })
            calls_graph.append({
                "source": f"{controller_class}.{method_name}",
                "target": f"{service_class}.{method_name}",
            })
            calls_graph.append({
                "source": f"{service_class}.{method_name}",
                "target": f"{mapper_class}.get",
            })

        elif method == "POST" and path == "/":
            method_name = f"create_{primary_entity.lower()}"
            controller_methods.append({
                "name": method_name,
                "http_method": "POST",
                "path": "/",
                "calls": [f"{service_class}.{method_name}"],
                "feature": desc or "创建",
            })
            service_methods.append({
                "name": method_name,
                "params": create_fields,
                "calls": [f"{mapper_class}.create"],
                "feature": desc or "创建",
            })
            mapper_methods.append({
                "name": "create",
                "params": create_fields,
                "feature": "创建",
            })
            calls_graph.append({
                "source": f"{controller_class}.{method_name}",
                "target": f"{service_class}.{method_name}",
            })
            calls_graph.append({
                "source": f"{service_class}.{method_name}",
                "target": f"{mapper_class}.create",
            })

    classes = [
        {
            "class_name": mapper_class,
            "type": "mapper",
            "file_name": f"{mapper_class}.py",
            "dependencies": [],
            "methods": mapper_methods,
        },
        {
            "class_name": service_class,
            "type": "service",
            "file_name": f"{service_class}.py",
            "dependencies": service_deps,
            "methods": service_methods,
        },
        {
            "class_name": controller_class,
            "type": "controller",
            "file_name": f"{controller_class}.py",
            "dependencies": [service_class],
            "methods": controller_methods,
        },
    ]

    files = [
        {"file_name": f"{mapper_class}.py", "class_name": mapper_class, "purpose": "数据访问层"},
        {"file_name": f"{service_class}.py", "class_name": service_class, "purpose": "业务逻辑层"},
        {"file_name": f"{controller_class}.py", "class_name": controller_class, "purpose": "HTTP 接口层"},
    ]

    return {
        "module_name": module_name,
        "api_prefix": prefix,
        "classes": classes,
        "files": files,
        "dependencies": cross_deps,
        "calls_graph": calls_graph,
    }


def _validate_architecture(arch: ArchitectureDoc) -> bool:
    """校验架构文档是否包含必要字段。"""
    if not arch.get("module_name") or not arch.get("api_prefix"):
        return False
    classes = arch.get("classes") or []
    types = {c.get("type") for c in classes}
    return {"mapper", "service", "controller"}.issubset(types)


def run_architect_node(state: PipelineState, kernel: Any) -> Dict[str, Any]:
    """
    LangGraph 流水线中的架构设计节点。

    输入 state.requirements_doc，输出 state.architecture_doc。
    """
    logs = list(state.get("logs", []))
    requirements_doc: Optional[RequirementsDoc] = state.get("requirements_doc")

    if not requirements_doc:
        logs.append("缺少需求文档，架构设计失败")
        return {"status": "requirements_missing", "logs": logs}

    data = invoke_json(ARCHITECT_SYSTEM_PROMPT, architect_prompt(requirements_doc))
    if data:
        arch: ArchitectureDoc = {
            "module_name": data.get("module_name", requirements_doc.get("module_name", "agent_demo_module")),
            "api_prefix": data.get("api_prefix", "/api/items"),
            "classes": data.get("classes", []),
            "files": data.get("files", []),
            "dependencies": data.get("dependencies", []),
            "calls_graph": data.get("calls_graph", []),
        }
        if _validate_architecture(arch):
            logs.append(f"LLM 生成架构: {arch['module_name']}, api_prefix={arch['api_prefix']}")
            return {
                "architecture_doc": arch,
                "status": "architecture_ready",
                "logs": logs,
            }

    arch = _build_architecture_from_requirements(requirements_doc)
    logs.append(f"使用回退架构: {arch['module_name']}, api_prefix={arch['api_prefix']}")
    return {
        "architecture_doc": arch,
        "status": "architecture_ready",
        "logs": logs,
    }
