"""
打包 API
========

在 8000 系统口暴露接口，触发 PyInstaller 将 8001 服务口打包为单文件可执行程序。
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from paas_core.kernel.microkernel import MicroKernel


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPEC_PATH = PROJECT_ROOT / "service_onefile.spec"


class BuildStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildRequest(BaseModel):
    """打包请求体。"""

    target: str = Field(
        default="current",
        description="目标平台：current（默认）/ windows / linux / macos",
    )


@dataclass
class BuildJob:
    """构建任务状态。"""

    job_id: str
    target: str
    status: BuildStatus = BuildStatus.PENDING
    artifact_path: Optional[Path] = None
    log: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class BuildJobStore:
    """内存构建任务存储。"""

    def __init__(self) -> None:
        self._jobs: dict[str, BuildJob] = {}
        self._current_job_id: Optional[str] = None

    def create(self, target: str) -> BuildJob:
        job_id = str(uuid.uuid4())
        job = BuildJob(job_id=job_id, target=target)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[BuildJob]:
        return self._jobs.get(job_id)

    def all(self) -> dict[str, BuildJob]:
        return dict(self._jobs)

    @property
    def current_job_id(self) -> Optional[str]:
        return self._current_job_id

    @current_job_id.setter
    def current_job_id(self, value: Optional[str]) -> None:
        self._current_job_id = value


_store = BuildJobStore()


def _artifact_path() -> Path:
    """根据当前平台返回预期产物路径。"""
    if platform.system() == "Windows":
        return PROJECT_ROOT / "dist" / "paas_service.exe"
    return PROJECT_ROOT / "dist" / "paas_service"


def _current_platform_name() -> str:
    """返回当前平台标识。"""
    return platform.system().lower()


def _pyinstaller_executable() -> str:
    """获取 PyInstaller 可执行命令。"""
    pyinstaller = shutil.which("pyinstaller")
    if pyinstaller:
        return pyinstaller
    return sys.executable


def _pyinstaller_args() -> list[str]:
    """构建 PyInstaller 调用参数。"""
    executable = _pyinstaller_executable()
    if executable == sys.executable:
        return [sys.executable, "-m", "PyInstaller", str(SPEC_PATH), "--clean", "--noconfirm"]
    return [executable, str(SPEC_PATH), "--clean", "--noconfirm"]


async def _read_stream(stream: asyncio.StreamReader, job: BuildJob) -> None:
    """异步读取子进程输出并追加到任务日志。"""
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip("\n")
        job.log.append(text)


async def _run_build(job_id: str) -> None:
    """在后台执行 PyInstaller 构建。"""
    job = _store.get(job_id)
    if job is None:
        return

    _store.current_job_id = job_id
    job.status = BuildStatus.BUILDING
    job.log.append(f"[{datetime.now().isoformat()}] 开始构建，目标: {job.target}")
    job.log.append(f"[{datetime.now().isoformat()}] 工作目录: {PROJECT_ROOT}")
    job.log.append(f"[{datetime.now().isoformat()}] 命令: {' '.join(_pyinstaller_args())}")

    try:
        process = await asyncio.create_subprocess_exec(
            *_pyinstaller_args(),
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.gather(
            _read_stream(process.stdout, job),
            _read_stream(process.stderr, job),
        )

        returncode = await process.wait()
        if returncode != 0:
            job.status = BuildStatus.FAILED
            job.error = f"PyInstaller 退出码: {returncode}"
            job.completed_at = datetime.now()
            return

        artifact = _artifact_path()
        if not artifact.exists():
            job.status = BuildStatus.FAILED
            job.error = f"构建完成但未找到产物: {artifact}"
            job.completed_at = datetime.now()
            return

        job.artifact_path = artifact
        job.status = BuildStatus.COMPLETED
        job.completed_at = datetime.now()
        job.log.append(f"[{datetime.now().isoformat()}] 构建完成: {artifact}")
    except Exception as exc:  # pragma: no cover
        job.status = BuildStatus.FAILED
        job.error = str(exc)
        job.completed_at = datetime.now()
        job.log.append(f"[{datetime.now().isoformat()}] 异常: {exc}")
    finally:
        _store.current_job_id = None


def _job_to_dict(job: BuildJob) -> dict:
    return {
        "job_id": job.job_id,
        "target": job.target,
        "status": job.status.value,
        "artifact_path": str(job.artifact_path) if job.artifact_path else None,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error,
        "log": job.log,
    }


def build_package_router(kernel: MicroKernel) -> APIRouter:
    """创建打包 API 路由器。"""
    router = APIRouter(tags=["package"])

    @router.post("/admin/kernel/package/service")
    async def trigger_build(payload: BuildRequest):
        """
        触发 8001 服务口单文件可执行程序打包。

        说明：
        - PyInstaller 不能跨平台编译，因此只能生成当前操作系统对应的产物。
        - 同时只能运行一个构建任务。
        """
        target = payload.target.lower()
        valid_targets = {"current", "windows", "linux", "macos"}
        if target not in valid_targets:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的目标平台: {payload.target}，可选: {sorted(valid_targets)}",
            )

        current = _current_platform_name()
        if target != "current" and target != current:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"PyInstaller 无法跨平台编译："
                    f"请求目标 {target}，当前平台 {current}。"
                    f"请在 {target} 系统上触发打包。"
                ),
            )

        if _store.current_job_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"已有构建任务正在运行: {_store.current_job_id}",
            )

        if not shutil.which("pyinstaller"):
            try:
                __import__("PyInstaller")
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="未检测到 PyInstaller，请先安装：pip install pyinstaller",
                )

        if not SPEC_PATH.exists():
            raise HTTPException(
                status_code=500,
                detail=f"PyInstaller spec 文件不存在: {SPEC_PATH}",
            )

        job = _store.create(target=target)
        # 启动后台构建任务
        asyncio.create_task(_run_build(job.job_id))

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "artifact_path": str(_artifact_path()),
            "message": "构建已启动",
        }

    @router.get("/admin/kernel/package/service/jobs/{job_id}")
    async def get_job_status(job_id: str):
        """查询构建任务状态与日志。"""
        job = _store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"找不到构建任务: {job_id}")
        return _job_to_dict(job)

    @router.get("/admin/kernel/package/service/jobs/{job_id}/download")
    async def download_artifact(job_id: str):
        """下载构建产物。"""
        job = _store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"找不到构建任务: {job_id}")
        if job.status != BuildStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"构建尚未完成，当前状态: {job.status.value}",
            )
        if not job.artifact_path or not job.artifact_path.exists():
            raise HTTPException(status_code=404, detail="构建产物不存在")

        filename = job.artifact_path.name
        return FileResponse(
            path=str(job.artifact_path),
            filename=filename,
            media_type="application/octet-stream",
        )

    return router
