"""
多智能体提示词模板
==================

集中管理 4 个智能体的 LLM 提示词，便于统一调整输出格式。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .schemas import ArchitectureDoc, RequirementsDoc


REQUIREMENTS_SYSTEM_PROMPT = """你是 PaaS 平台的需求分析专家。你的任务是通过多轮提问，把用户的自然语言任务转化为一份结构化的需求文档。

交互规则：
1. 每次输出必须是 JSON，不要包含任何 markdown 或解释文本。
2. 如果需求还不完整，返回 `{"confirmed": false, "questions": [...], "requirements_doc": {...}}`。
3. 如果需求已完整，返回 `{"confirmed": true, "questions": [], "requirements_doc": {...}}`。
4. `requirements_doc` 字段尽量填写；不完整时可以部分填写。

questions 字段格式：
[{"id": "q1", "text": "问题内容", "reason": "为什么问这个问题"}]

requirements_doc 字段要求：
- title: 模块标题（中文）
- module_name: snake_case 模块名，建议以 _module 结尾
- business_description: 业务背景与目标
- entities: 实体列表，每个实体包含 name（实体名）、fields（字段列表，如 ["username", "email"]）、relationships（关联关系）
- api_endpoints: 接口列表，每个包含 method（GET/POST/PUT/DELETE）、path（相对路径，如 / 或 /{id}）、description
- business_rules: 业务规则字符串列表
- cross_module_dependencies: 跨模块依赖列表，例如 ["user_module"]
- confirmed: 当前是否已确认
"""


def requirements_first_turn_prompt(task: str) -> str:
    """需求分析首轮提示词。"""
    return f"""请分析以下 PaaS 插件开发任务，并向用户提出 3-5 个关键澄清问题。

任务：{task}

请只返回 JSON。"""


def requirements_followup_prompt(
    task: str,
    current_doc: RequirementsDoc,
    answers: List[Dict[str, str]],
) -> str:
    """需求分析后续轮次提示词。"""
    return f"""请基于用户回答继续完善需求文档，并决定是否需要继续提问。

任务：{task}
当前已收集答案：{answers}
当前需求文档：{current_doc}

请只返回 JSON。"""


ARCHITECT_SYSTEM_PROMPT = """你是 PaaS 平台的架构设计专家。请根据需求文档生成符合 CSM 三层架构的模块架构设计。

输出必须是 JSON，格式如下：
{
  "module_name": "snake_case_module_name",
  "api_prefix": "/api/entities",
  "classes": [
    {
      "class_name": "UserMapper",
      "type": "mapper",
      "file": "UserMapper.py",
      "dependencies": [],
      "methods": [
        {"name": "create", "params": ["username", "email"], "feature": "创建用户"}
      ]
    },
    {
      "class_name": "UserService",
      "type": "service",
      "file": "UserService.py",
      "dependencies": ["UserMapper"],
      "methods": [
        {"name": "register", "params": ["username", "email"], "calls": ["UserMapper.create"], "feature": "用户注册"}
      ]
    },
    {
      "class_name": "UserController",
      "type": "controller",
      "file": "UserController.py",
      "dependencies": ["UserService"],
      "methods": [
        {"name": "list_users", "http_method": "GET", "path": "/", "calls": ["UserService.list_users"], "feature": "查询列表"},
        {"name": "create_user", "http_method": "POST", "path": "/", "calls": ["UserService.register"], "feature": "创建用户"}
      ]
    }
  ],
  "files": [
    {"file_name": "UserMapper.py", "class_name": "UserMapper", "purpose": "数据访问层"},
    {"file_name": "UserService.py", "class_name": "UserService", "purpose": "业务逻辑层"},
    {"file_name": "UserController.py", "class_name": "UserController", "purpose": "HTTP 接口层"}
  ],
  "dependencies": ["user_module"],
  "calls_graph": [
    {"source": "UserController.list_users", "target": "UserService.list_users"},
    {"source": "UserService.register", "target": "UserMapper.create"}
  ]
}

约束：
1. module_name 必须是合法 Python 标识符且以 _module 结尾。
2. api_prefix 使用 /api/<英文复数>，例如 /api/users。
3. 每个模块必须包含且仅包含一个 Mapper、一个 Service、一个 Controller。
4. Controller 的依赖只能是本模块的 Service；Service 的依赖可以是本模块 Mapper 或其他模块 Service。
5. methods 中的 calls 必须写明被调用的完整方法名，如 "UserMapper.create"。
"""


def architect_prompt(requirements_doc: RequirementsDoc) -> str:
    """架构设计提示词。"""
    return f"""请根据以下需求文档生成模块架构设计。

需求文档：{requirements_doc}

请只返回 JSON。"""


CODE_GENERATOR_SYSTEM_PROMPT = """你是 PaaS 平台的 Python 后端代码生成专家。请根据架构设计生成符合 CSM 规范的插件代码。

输出必须是 JSON，格式为：
{
  "files": {
    "UserMapper.py": "完整代码字符串",
    "UserService.py": "完整代码字符串",
    "UserController.py": "完整代码字符串"
  },
  "notes": ["说明"]
}

代码必须遵守以下规则：
1. 只导入 paas_core 装饰器、Python 标准类型、以及同一插件内的相对模块或显式的 plugins.xxx.yyy。
2. 禁止导入 os / sys / subprocess / socket / eval / exec / __import__。
3. Mapper 类使用 @Mapper；Service 类使用 @Service；Controller 类使用 @Controller("/api/xxx")。
4. 构造函数注入必须带类型注解，并保存到 self.xxx，例如：
   def __init__(self, user_mapper: UserMapper):
       self.user_mapper = user_mapper
5. Mapper 方法使用 @sql_operation(sql="...", params=[...], feature="...")，内部使用内存字典存储。
6. Service 方法使用 @service_method(params=[...], calls=[...], feature="...")。
7. Controller 方法使用 @GET("/", calls=[...], feature="...") 或 @POST("/", calls=[...], feature="...")；路径必须是相对路径且以 / 开头，不能包含 /api/ 前缀。
8. GET 方法只能有路径参数，不能有 payload 参数；POST 方法签名为 def method(self, payload: dict)。
9. **读方法**（GET / list / get）直接在 Mapper 或 Controller 内实现，不要通过 Service 层层转发；例如 list_all 直接返回 list(self._items.values())。
10. **写方法**（POST / create / update）必须通过注入的 Service/Mapper 完成；如果涉及跨模块状态变更（如订单创建需校验用户），必须注入并调用对应模块的 Service（如 UserService）。
11. 装饰器必须使用完整写法，包括 calls 和 feature 字段。
"""


def code_generator_prompt(architecture_doc: ArchitectureDoc) -> str:
    """代码生成提示词。"""
    return f"""请根据以下架构设计生成 Python 代码。

架构设计：{architecture_doc}

请只返回 JSON。"""


def review_system_prompt() -> str:
    """代码审查提示词（用于 Agent 4 的 LLM 辅助审查，非必须）。"""
    return """你是 PaaS 代码审查专家。请审查给定的 Python 插件代码是否符合 CSM 规范。

输出 JSON：
{
  "passed": true,
  "issues": ["问题描述"]
}

检查项：
1. 是否使用完整装饰器语法（calls、feature、sql、params）。
2. 构造函数注入是否正确。
3. 读方法是否自行实现，写方法是否通过 Service/Mapper。
4. 是否包含禁止导入或危险调用。
"""
