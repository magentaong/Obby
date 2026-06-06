from __future__ import annotations

from .models import AppConfig, NoteContext, Task, TaskKind


def classify_task(task: Task, config: AppConfig) -> Task:
    """Classifies a task based on tags and heading contexts."""
    tags = {tag.lower().strip() for tag in task.tags}

    # Tag-based classification (highest priority)
    for kind_name, kind_tags in config.task_type_tags.items():
        if any(tag.lower().strip() in tags for tag in kind_tags):
            task.kind = TaskKind(kind_name)
            task.classification_reason = f"Tag-matched {kind_name}"
            return task

    # Heading-based classification
    heading_text = " > ".join(task.heading_path).lower()
    for kind_name, phrases in config.heading_rules.items():
        if any(phrase.lower() in heading_text for phrase in phrases):
            task.kind = TaskKind(kind_name)
            task.classification_reason = f"Heading-matched {kind_name}"
            return task

    # Default fallback
    task.kind = TaskKind.UNKNOWN
    task.classification_reason = "No rules matched"
    return task


def classify_context(ctx: NoteContext, config: AppConfig) -> None:
    for task in ctx.all_tasks:
        classify_task(task, config)


def unknown_tasks(ctx: NoteContext) -> list[Task]:
    return [t for t in ctx.tasks if t.kind == TaskKind.UNKNOWN]
