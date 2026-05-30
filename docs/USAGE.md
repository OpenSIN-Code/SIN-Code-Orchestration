# Usage

## Install

```bash
pip install -e .
```

## Submit a task

```bash
sin-orch submit my-task coder '{"code": "def hello(): pass"}'
```

## Inspect status

```bash
sin-orch status
sin-orch query --task my-task
```

## Run a workflow

Create `workflow.yaml`:

```yaml
tasks:
  - task_id: plan
    role: planner
    input: {goal: "add caching layer"}
  - task_id: implement
    role: coder
    input: {target: "api/cache.py"}
    dependencies: [plan]
    verify: true
```

```bash
sin-orch workflow workflow.yaml
```

## Run the Context-Aware MCP server

```bash
sin-orch serve --host 127.0.0.1 --port 8770
```
