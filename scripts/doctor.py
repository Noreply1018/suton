from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import Callable

import psycopg
from redis import Redis
from rq.job import JobStatus
from rq import Queue, Worker
from rq.utils import import_attribute

from app.config import settings


Check = tuple[str, Callable[[], str]]


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"缺少必需命令：{name}")
    return path


def command(command_args: list[str]) -> str:
    result = subprocess.run(command_args, check=True, text=True, capture_output=True)
    output = result.stdout.strip() or result.stderr.strip()
    return output.splitlines()[0] if output else "ok"


def check_binaries() -> str:
    paths = [require_binary(binary) for binary in ("docker", "node", "pnpm", "uv")]
    return ", ".join(paths)


def check_pythonpath() -> str:
    import_attribute("app.processing.process_document")
    return "app.processing.process_document 可导入"


def check_dashscope_key() -> str:
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("缺少 DASHSCOPE_API_KEY，无法生成 Suton 要求的 DashScope embedding")
    return "已设置"


def check_docker() -> str:
    return command(["docker", "compose", "ps", "--status", "running"])


def check_database() -> str:
    with psycopg.connect(settings.database_url) as conn:
        row = conn.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'").fetchone()
        if not row:
            raise RuntimeError("PostgreSQL 可连接，但 pgvector extension 不存在")
    return "PostgreSQL/pgvector 可用"


def check_redis() -> str:
    redis = Redis.from_url(settings.redis_url)
    if not redis.ping():
        raise RuntimeError("Redis ping 失败")
    return "Redis 可用"


def check_worker() -> str:
    redis = Redis.from_url(settings.redis_url)
    workers = Worker.all(connection=redis)
    queue = Queue("suton", connection=redis)
    if not workers:
        raise RuntimeError("未发现 RQ worker；运行 make start 后再执行完整 doctor")
    queued_before = queue.count
    job = queue.enqueue("app.worker_health.rq_import_check", at_front=True, result_ttl=60, failure_ttl=300)
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline:
            job.refresh()
            status = job.get_status(refresh=False)
            if status == JobStatus.FINISHED:
                result = job.return_value(refresh=True) or {}
                if result.get("dashscope_api_key") != "set":
                    raise RuntimeError("worker 可执行任务，但缺少 DASHSCOPE_API_KEY")
                names = ", ".join(worker.name for worker in workers)
                return (
                    f"RQ worker 在线并可执行真实处理入口导入：{names}；"
                    f"检查前队列积压 {queued_before} 个任务，当前待处理 {queue.count} 个任务"
                )
            if status == JobStatus.FAILED:
                exc = (job.exc_info or "").strip().splitlines()
                detail = exc[-1] if exc else "健康检查任务失败"
                raise RuntimeError(f"worker 无法执行导入健康检查：{detail}")
            time.sleep(0.25)
        raise RuntimeError(
            f"worker 健康检查超时；检查前队列积压 {queued_before} 个任务，"
            "可能是 worker 忙碌、未消费队列或运行环境异常"
        )
    finally:
        try:
            job.cancel()
        except Exception:  # noqa: BLE001
            pass
        try:
            job.delete()
        except Exception:  # noqa: BLE001
            pass


def run_checks(checks: list[Check]) -> int:
    failed = False
    for label, func in checks:
        try:
            detail = func()
            print(f"[OK] {label}: {detail}")
        except Exception as exc:  # noqa: BLE001
            failed = True
            print(f"[FAIL] {label}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Suton v0.1.0 local runtime diagnostics")
    parser.add_argument("--preflight", action="store_true", help="只检查启动前必须满足的条件")
    args = parser.parse_args()

    checks: list[Check] = [
        ("本地命令", check_binaries),
        ("RQ 任务导入路径", check_pythonpath),
        ("DashScope 凭据", check_dashscope_key),
        ("Docker 服务", check_docker),
        ("数据库", check_database),
        ("Redis", check_redis),
    ]
    if not args.preflight:
        checks.append(("RQ worker", check_worker))
    raise SystemExit(run_checks(checks))


if __name__ == "__main__":
    main()
