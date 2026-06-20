from __future__ import annotations

from .models import AppConfig, Task


def format_task_packet(tasks: list[Task]) -> str:
    if not tasks:
        return "No candidate tasks found."

    blocks: list[str] = []

    for task in tasks:
        blocks.append(
            "\n".join(
                [
                    f"TASK {task.id}",
                    f"kind: {task.kind.value}",
                    f"week: {task.week or '-'}",
                    f"module: {task.module or '-'}",
                    f"source: {task.source_label}",
                    f"heading: {task.heading_label or '-'}",
                    f"text: {task.text}",
                ]
            )
        )

    return "\n\n".join(blocks)


def make_weekly_prompt(config: AppConfig, week: int) -> str:
    return (
        f"I am on Week {week} of a {config.total_weeks}-week {config.use_case} workflow.\n"
        "Tell me what should be done, what is current, what is behind, what is upcoming, "
        "and a realistic plan for the rest of this week. Use source file names as evidence."
    )


def make_today_prompt(config: AppConfig, week: int) -> str:
    return (
        f"I am on Week {week} of {config.total_weeks}. Help me plan today.\n"
        "Give exactly: Main task, Backup task, Tiny task if tired, Why, Evidence. "
        "Prefer 2-hour focus blocks and do not invent tasks."
    )


def make_focus_prompt(config: AppConfig, week: int) -> str:
    return (
        f"Pick my next 2-hour focus block for Week {week}.\n"
        "Prioritize required current or behind work, deadlines, and blocked-risk items. "
        "Give a main task, backup task, tiny version, stop condition, and evidence."
    )


def make_grounded_action_prompt(
    config: AppConfig,
    week: int,
    intent: str,
    candidates: list[Task],
) -> str:
    # If the intent is for planning, use a more flexible format
    if "plan" in intent.lower():
        return f"""
Intent: {intent}
Current week: {week} of {config.total_weeks}

You must choose only from the candidate tasks below.

Candidate tasks:
{format_task_packet(candidates)}

Rules:
- Provide a realistic sequence of tasks to focus on.
- Start with a "Strategic Thinking" section where you explain your reasoning.
- Cite specific task IDs and source files for every recommendation.
- Do not invent tasks or chores.
- Keep the plan practical and supportive.
""".strip()

    return f"""
Intent: {intent}
Current week: {week} of {config.total_weeks}

You must choose only from the candidate tasks below.
Every recommendation must include the exact TASK id and source file citation.

Candidate tasks:
{format_task_packet(candidates)}

Please provide your recommendation in the following natural structure:

### Thinking
Explain your reasoning for picking these specific tasks based on the current week and priorities.

### Recommendations
- **Main Quest**: [TASK ID] [Task Text] (Source)
- **Backup Quest**: [TASK ID] [Task Text] (Source)
- **Low Energy version**: [Smallest useful version of the main quest]
""".strip()


def make_weekly_draft_prompt(
    config: AppConfig,
    week: int,
    progress_update: str,
    current: list[Task],
    behind: list[Task],
    blocked: list[Task],
    stretch: list[Task],
    completed: list[Task],
) -> str:
    return f"""
Generate an Obsidian-compatible weekly planning draft for a specific week.

IMPORTANT: Look at the User Progress Update below. If the user mentions planning for a specific week (e.g., "Week 5 planning"), use THAT week number for the draft. Otherwise, assume Week {week}.

User Progress Update:
{progress_update}

Candidate Current Tasks (extracted from notes for current temporal week):
{format_task_packet(current)}

Behind Tasks:
{format_task_packet(behind)}

Blocked Tasks:
{format_task_packet(blocked)}

Stretch Tasks:
{format_task_packet(stretch)}

Completed Tasks (for context):
{format_task_packet(completed[:20])}

Rules:
- START WITH A "### Thinking" SECTION. Analyze the user's progress update and the extracted tasks. Determine which week you are actually planning for. Explain your strategy.
- Do not invent tasks.
- If unsure, put it under "Notes / Assumptions".
- Produce Obsidian-compatible Markdown.
- Keep it practical and not overly verbose.
- Use the structure below for the actual draft.

# Week [N] Overview

## Strategy
Short summary of the week.

## Completed / Progress
- items inferred from progress update or completed tasks

## Carried Over
- unfinished required tasks from previous/current week

## Main Quests
- required current tasks

## Module Focus
### [Module Name]
- tasks

## Blockers / Risks
- blocked or risky items

## Stretch Goals
- stretch tasks only

## Daily Suggested Flow
- Monday:
- Tuesday:
- Wednesday:
- Thursday:
- Friday:
- Weekend:

## Notes / Assumptions
- mention uncertainty instead of inventing
""".strip()


def make_grounded_today_plan_prompt(
    config: AppConfig,
    week: int,
    candidates: list[Task],
) -> str:
    return f"""
Help me plan my day for Week {week}.
You must choose only from the candidate tasks below.

Candidate tasks:
{format_task_packet(candidates)}

Rules:
- Start with a "Strategy & Reasoning" section explaining why you chose these specific items for today.
- Suggest a realistic schedule with 3-4 main focus blocks.
- Every task MUST include the exact TASK ID and source file citation.
- Do not invent tasks or suggest generic activities.

Structure:
# Daily Plan - Week {week}

## Strategy & Reasoning
[Explain your thinking here]

## Focus Blocks
1. [TASK ID] [Task Text] (Source) - [Why this first?]
2. ... and so on.
""".strip()


def build_system_prompt(config: AppConfig, context: str, week: int) -> str:
    modules = "\n".join(
        f"- {module.key}: {module.name}" for module in config.module_rules
    )
    style_rules = "\n".join(f"- {rule}" for rule in config.llm_style_rules)
    return f"""
Identity:
{config.llm_identity}

Mission:
{config.llm_mission}

Configured assistant name: {config.app_name}
Subtitle: {config.subtitle}
Use case mode: {config.use_case}
Current week: {week} of {config.total_weeks}

Known modules:
{modules}

Critical rules:
- Remember that you are Obby, the user's local Obsidian planning assistant.
- STRICT GROUNDING: Use ONLY information visible in the Obsidian context below.
- NO GENERIC ADVICE: Do not provide general productivity tips, morning routines, or generic task ideas.
- If the context is empty or does not contain relevant tasks, say: "I don't see any relevant information in your notes."
- For planning commands, obey the candidate task packet over broad context.
- Never invent work items, admin chores, emails, meetings, prep material, or deadlines.
- Never recommend a task unless you can cite its exact source file and line.
- Always cite source file names as evidence.
- Required/core tasks matter for progress.
- Stretch tasks are bonus work.
- Optional/idea tasks do not count as behind.
- Blocked tasks should be surfaced but not blamed.
- Prefer practical 2-hour focus blocks.
- Keep answers concise, direct, and supportive.
- Avoid markdown tables in assistant replies.

Configured style rules:
{style_rules or "- No extra style rules configured."}

Preferred next-action format:
### Thinking
[Reasoning]

### Recommendations
- **Main Quest**: [Task]
- **Backup Quest**: [Task]
- **Low Energy**: [Task]

Obsidian context:

{context}
""".strip()


def reset_messages(config: AppConfig, context: str, week: int) -> list[dict[str, str]]:
    return [{"role": "system", "content": build_system_prompt(config, context, week)}]


def make_identity_reminder(config: AppConfig, week: int) -> str:
    style_rules = "\n".join(f"- {rule}" for rule in config.llm_style_rules)
    return f"""
You are answering as {config.app_name}.

Identity:
{config.llm_identity}

Mission:
{config.llm_mission}

Current context:
- Assistant name: {config.app_name}
- Subtitle: {config.subtitle}
- Use case: {config.use_case}
- Current week: {week} of {config.total_weeks}

Rules for this reply:
- Do not claim to be a generic chatbot.
- If asked who you are, say you are {config.app_name}, the user's local-first Obsidian planning assistant.
- Stay grounded in the user's extracted notes when discussing tasks, plans, deadlines, or priorities.
- If something is not visible in the notes, say that {config.app_name} does not see it in the notes.
- Do not state that you are {config.app_name} unless prompted.

Style rules:
{style_rules or "- No extra style rules configured."}
""".strip()


def wrap_user_prompt(config: AppConfig, week: int, prompt: str) -> str:
    return f"""
{make_identity_reminder(config, week)}

User request:
{prompt}
""".strip()
