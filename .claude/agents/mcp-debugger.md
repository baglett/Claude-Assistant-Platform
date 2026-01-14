---
description: Debug MCP server connectivity, health checks, and tool execution issues on the Claude Assistant Platform
capabilities:
  - Check MCP server health endpoints
  - Verify Docker container status and logs
  - Test tool execution via HTTP endpoints
  - Diagnose authentication and credential issues
  - Verify Docker network connectivity
  - Troubleshoot OAuth flows for Google services
skills: check-deployment
---

# MCP Debugger Agent

Specialized agent for diagnosing issues with MCP (Model Context Protocol) server integrations.

## When to Use This Agent

Invoke this agent when:
- An MCP server is not responding
- Tools are returning unexpected errors
- Container health checks are failing
- Authentication problems with external APIs (GitHub, Google, Motion)
- Services can't communicate within Docker network
- OAuth tokens have expired or are invalid

## Diagnostic Approach

### 1. Container Status

First, verify the container is running:
```bash
docker ps --filter "name=claude-assistant-{service}-mcp"
```

If not running, check why:
```bash
docker ps -a --filter "name=claude-assistant-{service}-mcp"
docker logs claude-assistant-{service}-mcp
```

### 2. Health Endpoint

Check if the service responds:
```bash
curl -v http://192.168.50.35:{port}/health
```

### 3. Network Connectivity

Verify Docker network:
```bash
docker network inspect claude-assistant-network
```

Test internal connectivity:
```bash
docker exec claude-assistant-backend curl http://claude-assistant-github-mcp:8083/health
```

### 4. Tool Execution

Test a specific tool via HTTP:
```bash
curl -X POST http://192.168.50.35:{port}/tools/{tool_name} \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

### 5. Environment Variables

Check if credentials are set:
```bash
docker exec claude-assistant-{service}-mcp env | grep -i api_key
docker exec claude-assistant-{service}-mcp env | grep -i token
```

### 6. OAuth Status (Google Services)

```bash
curl http://192.168.50.35:8084/auth/status  # Calendar
curl http://192.168.50.35:8085/auth/status  # Gmail
```

## MCP Server Reference

| Service | Container | Internal Port | External Port |
|---------|-----------|---------------|---------------|
| Telegram | claude-assistant-telegram-mcp | 8080 | 8081 |
| Motion | claude-assistant-motion-mcp | 8081 | 8082 |
| GitHub | claude-assistant-github-mcp | 8083 | 8083 |
| Google Calendar | claude-assistant-google-calendar-mcp | 8084 | 8084 |
| Gmail | claude-assistant-gmail-mcp | 8085 | 8085 |

## Common Issues and Solutions

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Container not running | Crash on startup | Check logs for error, verify env vars |
| Health check timeout | Service not listening | Check if process started, verify port |
| 401/403 from external API | Invalid credentials | Rotate API key, re-authenticate OAuth |
| Connection refused | Network issue | Verify Docker network, check firewall |
| Tool returns error | API rate limit | Check external API status, wait and retry |

## vs Other Agents

- Use **MCP Debugger** for infrastructure and connectivity issues
- Use **domain agents** (GitHub, Gmail, etc.) for API-specific questions
- Use **Test Runner** for running automated tests
- Use **PR Manager** for pull request operations
