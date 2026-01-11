# Documentation Rules

These rules govern documentation updates for the Claude Assistant Platform.

## Documentation Files

| File | Purpose | Update When |
|------|---------|-------------|
| `README.md` | Quick start, installation, basic usage | Installation steps change, new prerequisites added |
| `CHANGELOG.md` | Detailed change history | Any notable change (features, fixes, breaking changes) |
| `DOCUMENTATION/ARCHITECTURE.md` | System design, data flows, component details | New services, agents, MCP servers, or architectural changes |
| `DOCUMENTATION/REQUIREMENTS.md` | Functional/non-functional requirements | Requirements change or new requirements added |
| `DOCUMENTATION/DEPLOYMENT.md` | Ports, containers, credentials, environment variables | New services, port changes, new env vars, credential additions |
| `DOCUMENTATION/TODO_Implementation.md` | Todo system implementation reference | Todo system changes |
| `DOCUMENTATION/apple-watch-shortcut.md` | Apple Watch setup guide | Shortcut flow or TG Watch integration changes |

## When to Update Documentation

### ALWAYS Update

1. **New MCP Server Added**
   - `DOCUMENTATION/DEPLOYMENT.md`: Add to port tables, container tables, env vars, health checks
   - `DOCUMENTATION/ARCHITECTURE.md`: Add to MCP Servers section, update diagrams
   - `CHANGELOG.md`: Document the addition

2. **New Agent Added**
   - `DOCUMENTATION/ARCHITECTURE.md`: Add to Sub-Agents table
   - `CHANGELOG.md`: Document the addition

3. **API Endpoint Changes**
   - `DOCUMENTATION/ARCHITECTURE.md`: Update endpoint tables
   - `CHANGELOG.md`: Document additions/changes/removals

4. **Environment Variable Changes**
   - `DOCUMENTATION/DEPLOYMENT.md`: Update env var tables
   - `.env.example`: Add with placeholder value and comment

5. **Port Allocation Changes**
   - `DOCUMENTATION/DEPLOYMENT.md`: Update all port tables (prod, dev, strategy)

6. **Database Schema Changes**
   - `CHANGELOG.md`: Document migration details
   - `DOCUMENTATION/ARCHITECTURE.md`: Update data model sections if significant

### Update If Relevant

- **Bug Fixes**: `CHANGELOG.md` only
- **Refactoring**: `CHANGELOG.md` if it affects public interfaces
- **Dependency Updates**: `CHANGELOG.md` for security or breaking updates

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:

```markdown
## [Unreleased]

### Section Title (Feature/Component Name)

**Category:**
- Bullet point describing change
- Another bullet point

**Another Category:**
- Details here
```

### Categories to Use

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features to be removed in future
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related changes

## Documentation Style

### Tables

Use tables for structured data (ports, env vars, endpoints):

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
```

### Code Blocks

Always specify language for syntax highlighting:

```markdown
```python
def example():
    pass
```
```

### ASCII Diagrams

Use ASCII diagrams for architecture flows:

```
┌─────────┐     ┌─────────┐
│  Box 1  │────►│  Box 2  │
└─────────┘     └─────────┘
```

## MCP Server Documentation Checklist

When adding a new MCP server, update these locations in `DOCUMENTATION/DEPLOYMENT.md`:

- [ ] Port Configuration → Production Deployment table
- [ ] Port Configuration → Local Development table
- [ ] Port Configuration → Port Allocation Strategy list
- [ ] Container Reference → Production Containers table
- [ ] Container Reference → Development Containers table
- [ ] Network Configuration → Internal Service Discovery table
- [ ] Jenkins Credentials table (if new credentials needed)
- [ ] Environment Variables section (new subsection if needed)
- [ ] Infrastructure Endpoints → Production table
- [ ] Quick Reference Commands → View Container Logs
- [ ] Quick Reference Commands → Health Checks
- [ ] Changelog table at bottom

## File Location Rules

- **User-facing guides**: `DOCUMENTATION/` folder
- **Development guides**: `README.md` in relevant subdirectory
- **API documentation**: Inline docstrings + `DOCUMENTATION/ARCHITECTURE.md`
- **Planning documents**: Delete after implementation (avoid stale plans)

## Anti-Patterns

- **DON'T** leave planning documents after implementation is complete
- **DON'T** have duplicate documentation files (root + DOCUMENTATION)
- **DON'T** document time estimates or schedules
- **DON'T** leave unchecked TODO items in completed documentation
- **DON'T** reference Python versions or dependencies that have changed
