from __future__ import annotations

from .models import AppConfig, NoteContext, Task, TaskKind


def classify_task(task: Task, config: AppConfig) -> Task:
    """Classifies a task based on tags and heading contexts, supporting multiple kinds."""
    tags = {tag.lower().strip() for tag in task.tags}
    matched_kinds: set[TaskKind] = set()
    reasons: list[str] = []

    # Tag-based matching
    for kind_name, kind_tags in config.task_type_tags.items():
        if any(tag.lower().strip() in tags for tag in kind_tags):
            try:
                kind = TaskKind(kind_name)
                matched_kinds.add(kind)
                reasons.append(f"Tag-matched {kind_name}")
            except ValueError:
                # If the config has a key not in TaskKind, we log reason but don't crash
                reasons.append(f"Tag-matched unknown kind: {kind_name}")

    # Heading-based matching
    heading_text = " > ".join(task.heading_path).lower()
    for kind_name, phrases in config.heading_rules.items():
        if any(phrase.lower() in heading_text for phrase in phrases):
            try:
                kind = TaskKind(kind_name)
                matched_kinds.add(kind)
                reasons.append(f"Heading-matched {kind_name}")
            except ValueError:
                reasons.append(f"Heading-matched unknown kind: {kind_name}")

    if not matched_kinds:
        task.kind = TaskKind.UNKNOWN
        task.all_kinds = [TaskKind.UNKNOWN]
        task.classification_reason = " | ".join(reasons) if reasons else "No rules matched"
        return task

    # Sort kinds by priority
    priority = [
        TaskKind.URGENT,
        TaskKind.REQUIRED,
        TaskKind.BLOCKED,
        TaskKind.STRETCH,
        TaskKind.OPTIONAL,
        TaskKind.IDEA,
    ]
    
    # Store all matched kinds
    task.all_kinds = sorted(list(matched_kinds), key=lambda k: priority.index(k) if k in priority else 999)
    
    # Pick the highest priority kind as primary
    task.kind = task.all_kinds[0]
    task.classification_reason = " | ".join(reasons)
    
    return task


def classify_context(ctx: NoteContext, config: AppConfig) -> None:
    for task in ctx.all_tasks:
        classify_task(task, config)


def unknown_tasks(ctx: NoteContext) -> list[Task]:
    return [t for t in ctx.tasks if t.kind == TaskKind.UNKNOWN]
