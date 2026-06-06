from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from .models import AppConfig, NoteContext, Task

# --- REGEX REGISTRY ---
TAG_RE = re.compile(r"#[A-Za-z0-9_./-]+")
WEEK_RE = re.compile(r"(?:#week/|[Ww]eek\s+)(\d+)")
TASK_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")
DEADLINE_RE = re.compile(r"(deadline|due|urgent|priority|📅)", re.IGNORECASE)


def scan_notes(config: AppConfig) -> NoteContext:
    """Scans the target folder for Markdown tasks and context."""
    ctx = NoteContext(target_folder=config.target_folder)
    folder = config.target_folder

    if not folder.exists():
        ctx.errors.append(f"Folder not found: {folder}")
        return ctx

    # Prioritize outline files in processing order
    all_files = sorted(folder.rglob("*.md"))
    files_to_scan = [f for f in all_files if not _is_ignored(f, config)]
    
    next_id = 1
    for file_path in files_to_scan:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            next_id = _parse_file(content, file_path, ctx, config, next_id)
        except OSError as exc:
            ctx.errors.append(f"Disk read error at {file_path.name}: {exc}")

    return ctx


def _parse_file(content: str, path: Path, ctx: NoteContext, config: AppConfig, start_id: int) -> int:
    useful_lines: list[str] = []
    heading_stack: list[str] = []
    in_code_block = False
    next_id = start_id

    for line_num, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        
        # Guard against code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Header tracking
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = _clean_text(stripped.lstrip("# "))
            heading_stack = heading_stack[: max(level - 1, 0)]
            heading_stack.append(title)
            useful_lines.append(f"{'#' * level} {title}")
            continue

        # Task extraction
        match = TASK_RE.match(raw_line)
        if match:
            is_done = match.group(1).lower() == "x"
            text = _clean_text(match.group(2))
            if not text:
                continue
                
            task = Task(
                id=next_id,
                text=text,
                source_file=path,
                line_number=line_num,
                checked=is_done,
                heading_path=list(heading_stack),
                tags=TAG_RE.findall(text),
                week=_extract_week(text),
                module=_extract_module(text, config),
            )
            
            target = ctx.completed_tasks if is_done else ctx.tasks
            target.append(task)
            useful_lines.append(text)
            next_id += 1
            continue

        # Metadata/Context lines
        if DEADLINE_RE.search(stripped):
            ctx.deadlines.append(f"[{path.name}:{line_num}] {stripped}")
            useful_lines.append(stripped)
        elif WEEK_RE.search(stripped):
            ctx.weekly_items.append(f"[{path.name}:{line_num}] {stripped}")
            useful_lines.append(stripped)

    # Context compression
    _integrate_context(path, useful_lines[:config.max_lines_per_file], ctx, config)
    return next_id


def _integrate_context(path: Path, lines: list[str], ctx: NoteContext, config: AppConfig) -> None:
    if not lines:
        return
        
    ctx.files_used.append(path)
    header = f"\n--- SOURCE: {path.name} ---"
    ctx.raw_chunks.extend([header] + lines)
    
    # Check if this file is a module outline
    is_outline = any(
        out.lower() in path.stem.lower() 
        for mod in config.module_rules 
        for out in mod.outline_names
    )
    
    if is_outline:
        ctx.module_outlines.extend([header] + lines)
    else:
        ctx.general_context.extend(lines)


def _is_ignored(path: Path, config: AppConfig) -> bool:
    return any(k and k in str(path) for k in config.ignore_keywords)

def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.rstrip()).strip()

def _extract_week(text: str) -> int | None:
    match = WEEK_RE.search(text)
    return int(match.group(1)) if match else None

def _extract_module(text: str, config: AppConfig) -> str | None:
    lowered = text.lower()
    for mod in config.module_rules:
        if any(tag.lower() in lowered for tag in mod.tags):
            return mod.key
    return None


def build_context_string(ctx: NoteContext, config: AppConfig, week: int | None) -> str:
    parts = []
    if week:
        parts.append(f"[CURRENT WEEK: {week} of {config.total_weeks}]")
        
    sections = [
        ("MODULE OUTLINES", ctx.module_outlines),
        ("DEADLINES", ctx.deadlines),
        ("WEEKLY PACING", ctx.weekly_items),
        ("UNCHECKED TASKS", [f"[{t.source_label}] {t.text} ({t.kind.value})" for t in ctx.tasks]),
        ("COMPLETED TASKS", [f"[{t.source_label}] {t.text}" for t in ctx.completed_tasks[:40]]),
        ("GENERAL HEADINGS", ctx.general_context),
    ]
    
    for title, data in sections:
        if data:
            parts.extend([f"\n=== {title} ===", *data])

    context = "\n".join(parts)
    if len(context) > config.max_total_context_chars:
        return context[:config.max_total_context_chars] + "\n\n[CONTEXT TRUNCATED]"
    return context
