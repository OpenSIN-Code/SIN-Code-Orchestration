"""CLI für den Orchestration-Daemon."""
from __future__ import annotations

import json
import typer
from pathlib import Path

import yaml

from .orchestrator import Orchestrator, TaskSpec, Role
from .shared_context import ContextStatus

app = typer.Typer(help="SIN-Code Advanced Orchestration CLI")


def _config_path() -> str | None:
    for p in (Path("config.yaml"), Path(".sin/orchestration.yaml")):
        if p.exists():
            return str(p)
    return None


@app.command()
def submit(
    task_id: str,
    role: Role,
    input_json: str = typer.Argument(..., help="JSON input data"),
    dependencies: list[str] = typer.Option([], "--dep"),
    verify: bool = typer.Option(True, "--verify/--no-verify"),
):
    """Submit a new task to the orchestrator."""
    orch = Orchestrator(config_path=_config_path())

    spec = TaskSpec(
        task_id=task_id,
        description=f"Task via CLI: {task_id}",
        role=role,
        input_data=json.loads(input_json),
        dependencies=dependencies,
        require_verification=verify,
    )
    entry = orch.submit_task(spec)
    typer.echo(json.dumps({"entry_id": entry.id, "status": entry.status.value}, indent=2))


@app.command()
def status(task_id: str = typer.Option(None, "--task")):
    """Show status of tasks."""
    orch = Orchestrator(config_path=_config_path())
    typer.echo(json.dumps(orch.status(task_id), indent=2))


@app.command()
def query(
    task_id: str = typer.Option("", "--task"),
    agent_id: str = typer.Option("", "--agent"),
    status: str = typer.Option("", "--status"),
):
    """Query context entries by filters."""
    from .shared_context import SharedContextStore
    cfg = {}
    cp = _config_path()
    if cp:
        with open(cp) as f:
            cfg = yaml.safe_load(f) or {}
    ctx_cfg = cfg.get("context_store", {})
    store = SharedContextStore(
        backend=ctx_cfg.get("backend", "memory"),
        redis_url=ctx_cfg.get("redis_url"),
        namespace=ctx_cfg.get("namespace"),
    )
    entries = store.query(
        task_id=task_id or None,
        agent_id=agent_id or None,
        status=ContextStatus(status) if status else None,
    )
    typer.echo(json.dumps([{
        "id": e.id, "task_id": e.task_id, "agent_id": e.agent_id,
        "role": e.role, "status": e.status.value,
    } for e in entries], indent=2))


@app.command()
def serve(host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8770)):
    """Run the Context-Aware MCP server."""
    from .ca_mcp import ContextAwareMCP
    server = ContextAwareMCP(_config_path() or "config.yaml")
    server.run(host=host, port=port)


@app.command()
def workflow(workflow_file: Path):
    """Execute a workflow from a YAML file."""
    with open(workflow_file) as f:
        wf = yaml.safe_load(f)

    orch = Orchestrator(_config_path())
    tasks = [
        TaskSpec(
            task_id=t["task_id"],
            description=t.get("description", ""),
            role=Role(t["role"]),
            input_data=t.get("input", {}),
            dependencies=t.get("dependencies", []),
            require_verification=t.get("verify", True),
        )
        for t in wf.get("tasks", [])
    ]
    results = orch.run_workflow(tasks)
    typer.echo(json.dumps({
        tid: {
            "success": r.success,
            "error": r.error,
            "duration": r.duration_seconds,
            "verified": r.verification_passed,
        }
        for tid, r in results.items()
    }, indent=2))


if __name__ == "__main__":
    app()
