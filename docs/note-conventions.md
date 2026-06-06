# Note Conventions

Obby does not require one exact vault structure, but it works best when notes use
plain Markdown tasks and consistent tags or headings.

## Minimum Supported Format

```md
- [ ] Unfinished task
- [x] Finished task
```

Obby scans `.md` files under `TARGET_FOLDER` and ignores files/folders matching
`IGNORE_KEYWORDS`.

## Recommended Task Types

Use tags:

```md
- [ ] Submit assignment #required
- [ ] Add polish pass #stretch
- [ ] Try an alternate idea #optional
- [ ] Build future feature #idea
- [ ] Waiting on access #blocked
```

Or headings:

```md
## Required
- [ ] Submit assignment

## Stretch Goals
- [ ] Add polish pass

## Blocked
- [ ] Waiting on access
```

Both systems are configurable in `TASK_TYPE_TAGS` and `HEADING_RULES`.

## Weeks

Use week tags when possible:

```md
- [ ] Finish module outline #week/3
```

Obby also detects text like `Week 3`, but explicit tags are cleaner.

## Modules And Projects

Use module tags:

```md
- [ ] Deploy API #module/backend
- [ ] Review cloud notes #module/aws
```

Configure modules in `MODULES`:

```python
MODULES = [
    {
        "key": "backend",
        "name": "Backend Engineering",
        "tags": ["#module/backend", "#backend"],
        "outline_names": ["Backend Module"],
    },
]
```

For project or work mode, modules can mean workstreams:

```python
MODULES = [
    {"key": "client", "name": "Client Work", "tags": ["#client"]},
    {"key": "ops", "name": "Operations", "tags": ["#ops"]},
]
```

## Suggested Profiles

Study:

```md
## Required
- [ ] Finish Week 2 lab #week/2 #module/cloud
```

Project:

```md
## Ship This Week
- [ ] Implement auth callback #required #module/backend
```

Work:

```md
## Must Do
- [ ] Send sprint update #required
```

Personal:

```md
## Life OS
- [ ] Plan meals #required
```

## Compatibility Tips

- Prefer real task text after `- [ ]`; blank placeholders are ignored.
- Use tags when a heading might be ambiguous.
- Add old or irrelevant folders to `IGNORE_KEYWORDS`.
- Use `/unknown` to see tasks Obby could not classify.
- Use `/classify` to manually classify unknowns in memory.
