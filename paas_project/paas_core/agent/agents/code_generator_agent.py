"""
代码生成智能体
==============

根据架构设计生成符合 CSM 规范的 Python 插件文件。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..llm_utils import invoke_json
from ..prompts import CODE_GENERATOR_SYSTEM_PROMPT, code_generator_prompt
from ..schemas import ArchitectureDoc, PipelineState


def _camel_to_snake(name: str) -> str:
    """CamelCase 转 snake_case。"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _render_mapper(arch: ArchitectureDoc) -> str:
    """渲染 Mapper 模板。"""
    mapper_class = next(
        (c for c in arch.get("classes", []) if c.get("type") == "mapper"),
        {"class_name": "ItemMapper", "methods": []},
    )
    class_name = mapper_class.get("class_name", "ItemMapper")

    methods = mapper_class.get("methods", [])
    if not methods:
        methods = [
            {"name": "create", "params": ["name"], "feature": "创建"},
            {"name": "get", "params": ["item_id"], "feature": "根据 ID 查询"},
            {"name": "list_all", "params": [], "feature": "全量列表"},
        ]

    lines = [
        '"""',
        f"{class_name} 数据访问层。",
        '"""',
        "",
        "from paas_core import Mapper, sql_operation",
        "",
        "@Mapper",
        f"class {class_name}:",
        "    def __init__(self):",
        "        self._items = {}",
        "        self._next_id = 1",
        "",
    ]

    for method in methods:
        name = method.get("name", "")
        params = method.get("params", [])
        feature = method.get("feature", name)
        sql = method.get("sql")

        if name == "create":
            sql = sql or "INSERT INTO items (name) VALUES (%s)"
            params_decl = ", ".join(f"{p}: str" for p in params) or "name: str"
            lines.extend([
                f'    @sql_operation(sql="{sql}", params={params!r}, feature="{feature}")',
                f"    def create(self, {params_decl}) -> dict:",
                f'        """{feature}。"""',
                "        item_id = self._next_id",
                "        self._next_id += 1",
                f"        item = {{'id': item_id, {', '.join(f'{chr(39)}{p}{chr(39)}: {p}' for p in (params or ['name']))}}}",
                "        self._items[item_id] = item",
                "        return item",
                "",
            ])
        elif name == "get":
            sql = sql or "SELECT * FROM items WHERE id = %s"
            param = params[0] if params else "item_id"
            params_decl = ", ".join(f"{p}: str" for p in params) or "item_id: str"
            lines.extend([
                f'    @sql_operation(sql="{sql}", params={params!r}, feature="{feature}")',
                f"    def get(self, {params_decl}) -> dict | None:",
                f'        """{feature}。"""',
                f"        return self._items.get({param})",
                "",
            ])
        elif name == "list_all":
            sql = sql or "SELECT * FROM items"
            lines.extend([
                f'    @sql_operation(sql="{sql}", feature="{feature}")',
                "    def list_all(self) -> list:",
                f'        """{feature}。"""',
                "        return list(self._items.values())",
                "",
            ])
        else:
            params_decl = ", ".join(f"{p}: str" for p in params)
            lines.extend([
                f'    @sql_operation(sql="{sql or "SELECT 1"}", params={params!r}, feature="{feature}")',
                f"    def {name}(self, {params_decl}):",
                f'        """{feature}。"""',
                "        pass",
                "",
            ])

    return "\n".join(lines)


def _render_service(arch: ArchitectureDoc) -> str:
    """渲染 Service 模板。"""
    classes = arch.get("classes", [])
    mapper_class = next((c for c in classes if c.get("type") == "mapper"), {"class_name": "ItemMapper"})
    service_class = next((c for c in classes if c.get("type") == "service"), {"class_name": "ItemService"})

    class_name = service_class.get("class_name", "ItemService")
    mapper_name = mapper_class.get("class_name", "ItemMapper")
    mapper_var = _camel_to_snake(mapper_name)

    deps = service_class.get("dependencies", [mapper_name])
    cross_service_imports = []
    init_params = []
    init_saves = []
    for dep in deps:
        if dep == mapper_name:
            init_params.append(f"{mapper_var}: {mapper_name}")
            init_saves.append(f"        self.{mapper_var} = {mapper_var}")
        elif dep.endswith("Service"):
            var = _camel_to_snake(dep)
            module = var.replace("_service", "_module")
            cross_service_imports.append(f"from plugins.{module}.{dep} import {dep}")
            init_params.append(f"{var}: {dep}")
            init_saves.append(f"        self.{var} = {var}")

    lines = [
        '"""',
        f"{class_name} 业务逻辑层。",
        '"""',
        "",
        "from paas_core import Service, service_method",
    ]
    if cross_service_imports:
        lines.extend(cross_service_imports)
    lines.append(f"from .{mapper_name} import {mapper_name}")
    lines.extend([
        "",
        "@Service",
        f"class {class_name}:",
        "    def __init__(self, " + ", ".join(init_params) + "):",
    ])
    lines.extend(init_saves)
    lines.append("")

    methods = service_class.get("methods", [])
    if not methods:
        methods = [
            {"name": "create_item", "params": ["name"], "calls": [f"{mapper_name}.create"], "feature": "创建"},
            {"name": "get_item", "params": ["item_id"], "calls": [f"{mapper_name}.get"], "feature": "查询"},
            {"name": "list_items", "params": [], "calls": [f"{mapper_name}.list_all"], "feature": "全量列表"},
        ]

    for method in methods:
        name = method.get("name", "")
        params = method.get("params", [])
        calls = method.get("calls", [])
        feature = method.get("feature", name)
        params_decl = ", ".join(f"{p}: str" for p in params)
        sig_params = params_decl if not params_decl else f", {params_decl}"

        body = "        pass"
        for call in calls:
            if ".create" in call:
                args = ", ".join(params)
                body = f"        return self.{mapper_var}.create({args})"
            elif ".get" in call:
                param = params[0] if params else "item_id"
                body = f"        return self.{mapper_var}.get({param})"
            elif ".list_all" in call:
                body = f"        return self.{mapper_var}.list_all()"
            elif "." in call:
                parts = call.split(".")
                if len(parts) == 2:
                    dep_class = parts[0]
                    dep_method = parts[1]
                    dep_var = _camel_to_snake(dep_class)
                    args = ", ".join(params)
                    body = f"        return self.{dep_var}.{dep_method}({args})"

        lines.extend([
            f'    @service_method(params={params!r}, calls={calls!r}, feature="{feature}")',
            f"    def {name}(self{sig_params}) -> dict | None:",
            f'        """{feature}。"""',
            body,
            "",
        ])

    return "\n".join(lines)


def _render_controller(arch: ArchitectureDoc) -> str:
    """渲染 Controller 模板。"""
    classes = arch.get("classes", [])
    service_class = next((c for c in classes if c.get("type") == "service"), {"class_name": "ItemService"})
    controller_class = next((c for c in classes if c.get("type") == "controller"), {"class_name": "ItemController"})

    class_name = controller_class.get("class_name", "ItemController")
    service_name = service_class.get("class_name", "ItemService")
    service_var = _camel_to_snake(service_name)
    api_prefix = arch.get("api_prefix", "/api/items")

    methods = controller_class.get("methods", [])
    if not methods:
        methods = [
            {"name": "list_items", "http_method": "GET", "path": "/", "calls": [f"{service_name}.list_items"], "feature": "查询列表"},
            {"name": "get_item", "http_method": "GET", "path": "/{item_id}", "calls": [f"{service_name}.get_item"], "feature": "查询"},
            {"name": "create_item", "http_method": "POST", "path": "/", "calls": [f"{service_name}.create_item"], "feature": "创建"},
        ]

    lines = [
        '"""',
        f"{class_name} HTTP 接口层。",
        '"""',
        "",
        "from paas_core import Controller, GET, POST",
        f"from .{service_name} import {service_name}",
        "",
        f'@Controller("{api_prefix}")',
        f"class {class_name}:",
        f"    def __init__(self, {service_var}: {service_name}):",
        f"        self.{service_var} = {service_var}",
        "",
    ]

    for method in methods:
        name = method.get("name", "")
        http_method = method.get("http_method", "GET")
        path = method.get("path", "/")
        calls = method.get("calls", [])
        feature = method.get("feature", name)

        if http_method == "GET":
            decorator = f'    @GET("{path}", calls={calls!r}, feature="{feature}")'
            if "{id}" in path or "{item_id}" in path:
                param_name = "item_id" if "{item_id}" in path else "id"
                lines.extend([
                    decorator,
                    f"    def {name}(self, {param_name}: str):",
                    f'        """{http_method} {api_prefix}{path}"""',
                    f"        item = self.{service_var}.{name}(int({param_name}))",
                    "        if item is None:",
                    '            return {"error": "not found"}',
                    "        return item",
                    "",
                ])
            else:
                lines.extend([
                    decorator,
                    f"    def {name}(self):",
                    f'        """{http_method} {api_prefix}{path}"""',
                    f"        return self.{service_var}.{name}()",
                    "",
                ])
        elif http_method == "POST":
            decorator = f'    @POST("{path}", calls={calls!r}, feature="{feature}")'
            service_method = calls[0].split(".")[-1] if calls else name
            lines.extend([
                decorator,
                f"    def {name}(self, payload: dict):",
                f'        """{http_method} {api_prefix}{path}"""',
                f"        return self.{service_var}.{service_method}(**payload)",
                "",
            ])

    return "\n".join(lines)


def _fallback_generate(arch: ArchitectureDoc) -> Dict[str, str]:
    """确定性代码生成回退。"""
    classes = arch.get("classes", [])
    mapper_file = next((c.get("file_name", f"{c['class_name']}.py") for c in classes if c.get("type") == "mapper"), "ItemMapper.py")
    service_file = next((c.get("file_name", f"{c['class_name']}.py") for c in classes if c.get("type") == "service"), "ItemService.py")
    controller_file = next((c.get("file_name", f"{c['class_name']}.py") for c in classes if c.get("type") == "controller"), "ItemController.py")
    return {
        mapper_file: _render_mapper(arch),
        service_file: _render_service(arch),
        controller_file: _render_controller(arch),
    }


def _is_valid_generated_files(files: Dict[str, str], arch: ArchitectureDoc) -> bool:
    """校验生成的代码是否满足 CSM 装配约定。"""
    if not files or len(files) < 3:
        return False

    expected_names = {c.get("file_name", "") for c in arch.get("classes", [])}
    arch_files = {c.get("file_name", "") for c in arch.get("files", [])}
    if arch_files and not expected_names:
        expected_names = arch_files

    mapper_file = next((f for f in files if f.endswith("Mapper.py")), None)
    service_file = next((f for f in files if f.endswith("Service.py")), None)
    controller_file = next((f for f in files if f.endswith("Controller.py")), None)

    if not all([mapper_file, service_file, controller_file]):
        return False

    if "@Mapper" not in files[mapper_file]:
        return False
    if "@Service" not in files[service_file]:
        return False
    if "@Controller" not in files[controller_file]:
        return False

    if not re.search(r"@Controller\s*\(\s*\"", files[controller_file]):
        return False

    if "def __init__(" not in files[service_file]:
        return False
    if "def __init__(" not in files[controller_file]:
        return False

    method_decorators = list(
        re.finditer(
            r"@(GET|POST|PUT|PATCH|DELETE)\s*\(\s*\"(.*?)\"\s*\)",
            files[controller_file],
        )
    )
    if not method_decorators:
        return False
    for m in method_decorators:
        http_method = m.group(1)
        method_path = m.group(2)
        if not method_path.startswith("/") or method_path.startswith("/api/"):
            return False
        subsequent = files[controller_file][m.end() :]
        def_match = re.search(r"def\s+\w+\s*\((.*?)\):", subsequent, re.DOTALL)
        if not def_match:
            return False
        params = def_match.group(1)
        if http_method == "GET" and "payload" in params:
            return False

    return True


def run_generator_node(state: PipelineState, kernel: Any) -> Dict[str, Any]:
    """
    LangGraph 流水线中的代码生成节点。

    输入 state.architecture_doc，输出 state.files。
    """
    logs = list(state.get("logs", []))
    arch: Optional[ArchitectureDoc] = state.get("architecture_doc")

    if not arch:
        logs.append("缺少架构文档，代码生成失败")
        return {"status": "architecture_missing", "logs": logs}

    data = invoke_json(CODE_GENERATOR_SYSTEM_PROMPT, code_generator_prompt(arch))
    files: Dict[str, str] = {}
    if data:
        candidate = data.get("files") or data
        if candidate and isinstance(candidate, dict):
            files = {k: v for k, v in candidate.items() if isinstance(v, str)}

    if _is_valid_generated_files(files, arch):
        logs.append(f"LLM 生成文件: {list(files.keys())}")
    else:
        logs.append("LLM 代码未满足 CSM 装配约束或解析失败，使用确定性模板")
        files = _fallback_generate(arch)

    return {
        "files": files,
        "status": "generated",
        "logs": logs,
    }
