# Claude Code Modular Rules

This directory contains modular rules for Claude Code that are automatically loaded based on the files being worked on.

## How Rules Work

1. **Always-loaded rules** (no `paths` frontmatter): Apply to all files
   - `project-overview.md` - Architecture and key patterns
   - `security.md` - Security requirements

2. **Path-specific rules** (with `paths` frontmatter): Only load when working on matching files
   - Example: `backend/agents.md` only loads when editing `Backend/src/agents/**/*.py`

## Directory Structure

```
rules/
├── README.md                 # This file
├── project-overview.md       # Always loaded
├── security.md               # Always loaded
├── backend/
│   ├── python.md             # Backend/**/*.py
│   ├── fastapi.md            # Backend/src/api/**/*.py
│   ├── agents.md             # Backend/src/agents/**/*.py
│   ├── database.md           # Backend/src/database/**/*.py, Backend/database/**/*.sql
│   └── pydantic-models.md    # Backend/src/models/**/*.py
├── frontend/
│   ├── nextjs.md             # Frontend/**/*.{ts,tsx}
│   └── react-components.md   # Frontend/src/components/**/*.tsx
├── mcp-servers/
│   └── fastmcp.md            # MCPS/**/*.py
└── infrastructure/
    ├── docker.md             # **/Dockerfile, **/docker-compose*.yml
    └── jenkins.md            # Jenkinsfile
```

## Adding New Rules

### 1. Create a new rule file

Create a `.md` file in the appropriate subdirectory.

### 2. Add path-specific frontmatter (optional)

If the rule should only apply to specific files, add YAML frontmatter:

```markdown
---
paths:
  - "path/to/files/**/*.ext"
  - "another/path/*.py"
---

# Rule Title

Your rules here...
```

### 3. Glob pattern syntax

| Pattern | Matches |
|---------|---------|
| `**/*.py` | All Python files in any directory |
| `src/**/*` | All files under src/ |
| `*.md` | Markdown files in root only |
| `src/**/*.{ts,tsx}` | TypeScript files under src/ |

### 4. Write focused, actionable rules

- Use imperative language ("Use type hints", not "Type hints should be used")
- Include code examples for patterns
- Keep each file focused on one topic
- Be specific ("Use 2-space indentation" vs "Format properly")

## Updating Existing Rules

1. **Find the relevant rule file** based on the file type you're working with
2. **Edit the markdown** to add, modify, or remove instructions
3. **Test the change** by working on a file that matches the paths
4. **Commit the change** with a descriptive message

## Best Practices

1. **Keep rules focused** - One topic per file
2. **Use descriptive filenames** - Name should indicate content
3. **Avoid duplication** - Global rules are in `~/.claude/CLAUDE.md`
4. **Update when patterns change** - Keep rules in sync with codebase
5. **Remove obsolete rules** - Delete rules for deprecated patterns

## Troubleshooting

### Rule not loading?

1. Check the `paths` frontmatter matches your file path
2. Ensure the glob pattern is correct (use `**` for recursive matching)
3. Verify the file is a valid `.md` file in `.claude/rules/`

### Rule loading when it shouldn't?

1. Check if the paths pattern is too broad
2. Consider making the pattern more specific

## References

- [Claude Code Memory Documentation](https://code.claude.com/docs/en/memory)
- [Glob Pattern Syntax](https://en.wikipedia.org/wiki/Glob_(programming))
