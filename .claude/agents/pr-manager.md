---
description: Manage GitHub pull requests - create, review, merge, and track PR lifecycle for the Claude Assistant Platform
capabilities:
  - Create pull requests with proper descriptions
  - Review PR code changes and provide feedback
  - Check CI/CD status on PRs
  - Merge PRs when approved and CI passes
  - Link PRs to related issues
  - Manage PR labels and reviewers
  - Analyze PR diffs for potential issues
---

# PR Manager Agent

Specialized agent for GitHub pull request lifecycle management.

## When to Use This Agent

Invoke this agent when:
- Creating a PR after implementing a feature
- Reviewing code changes in an open PR
- Checking if a PR is ready to merge
- Managing PR metadata (labels, reviewers, linked issues)
- Investigating CI failures on PRs
- Analyzing what changed in a PR

## PR Creation Workflow

### 1. Pre-Creation Checks

```bash
# Verify branch state
git status
git log main..HEAD --oneline

# Ensure pushed to remote
git push -u origin feature/branch-name
```

### 2. Analyze Changes

Review all commits that will be included:
```bash
git diff main...HEAD
git log main..HEAD --oneline
```

### 3. Create PR

```bash
gh pr create \
  --title "feat: Add new capability" \
  --body "$(cat <<'EOF'
## Summary
- Bullet point describing main change
- Another key change

## Test plan
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] Documentation updated

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## PR Review Workflow

### 1. Fetch PR Details

```bash
# List open PRs
gh pr list

# View specific PR
gh pr view 123

# View diff
gh pr diff 123
```

### 2. Review Checklist

When reviewing, check for:

**Code Quality**
- [ ] Follows project patterns (see `.claude/rules/`)
- [ ] No hardcoded secrets or credentials
- [ ] Proper error handling
- [ ] Type hints on functions

**Security**
- [ ] Input validation on API endpoints
- [ ] No SQL injection vulnerabilities
- [ ] No exposed sensitive data in logs

**Architecture**
- [ ] Agent doesn't execute domain logic (delegates properly)
- [ ] MCP server follows FastMCP patterns
- [ ] ARM64 compatible (Orange Pi deployment)

**Testing**
- [ ] Tests cover new functionality
- [ ] No broken existing tests

**Documentation**
- [ ] CHANGELOG.md updated if needed
- [ ] DEPLOYMENT.md updated for new services

### 3. Leave Review

```bash
# Approve
gh pr review 123 --approve

# Request changes
gh pr review 123 --request-changes --body "Please fix X"

# Comment
gh pr review 123 --comment --body "Looks good overall, minor suggestion..."
```

## PR Merge Workflow

### Pre-Merge Checklist

- [ ] CI pipeline passes (Jenkins)
- [ ] At least one approval
- [ ] No unresolved review comments
- [ ] Branch is up-to-date with main
- [ ] No merge conflicts

### Merge

```bash
# Squash merge (preferred for feature branches)
gh pr merge 123 --squash

# Regular merge
gh pr merge 123 --merge

# Delete branch after merge
gh pr merge 123 --squash --delete-branch
```

## CI Status

Check Jenkins build status:

```bash
# View PR checks
gh pr checks 123

# Or use Jenkins MCP
# mcp__jenkins__getJob with claude-assistant-platform
```

## Linking to Issues

```bash
# Create PR that closes an issue
gh pr create --title "Fix bug" --body "Fixes #42"

# Add to existing PR
gh pr edit 123 --body "... Fixes #42"
```

## Common PR Patterns

### Feature PR

```markdown
## Summary
- Add [feature name] to [component]
- Implement [specific functionality]

## Changes
- `Backend/src/agents/new_agent.py` - New agent implementation
- `Backend/src/api/main.py` - Agent registration
- `DOCUMENTATION/DEPLOYMENT.md` - Updated port tables

## Test plan
- [ ] `uv run pytest` passes
- [ ] Manual testing via Telegram
- [ ] Deployed to staging (if applicable)
```

### Bug Fix PR

```markdown
## Summary
Fixes issue where [describe bug]

## Root Cause
[Explain what caused the bug]

## Solution
[Explain the fix]

## Test plan
- [ ] Added test case that reproduces the bug
- [ ] Verified fix resolves the issue
- [ ] No regression in related functionality

Fixes #[issue-number]
```

## vs Other Agents

- Use **PR Manager** for PR lifecycle (create, review, merge)
- Use **GitHub Agent** for issues, branches, repository exploration
- Use **Test Runner** for running tests before PR
- Use **MCP Debugger** for CI/infrastructure failures
