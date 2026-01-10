# Jenkins MCP Server Plugin Setup for Claude Code

This guide walks through setting up the [Jenkins MCP Server Plugin](https://plugins.jenkins.io/mcp-server) to enable Claude Code to interact with your Jenkins instance.

## Overview

The Jenkins MCP Server Plugin implements the Model Context Protocol (MCP) server-side component, allowing Claude Code to:

- List and search Jenkins jobs
- Trigger builds with parameters
- Retrieve build logs and search for patterns
- Access build details, SCM info, and change sets
- Monitor Jenkins health status

## Prerequisites

- **Jenkins 2.533 or higher** - Check your version at `http://your-jenkins-url/about`
- **Admin access** to install plugins
- **Claude Code** installed on your development machine

## Step 1: Install the Plugin

1. Navigate to **Manage Jenkins** → **Plugins** → **Available plugins**
2. Search for **"MCP Server"**
3. Check the checkbox next to the plugin
4. Click **Install**
5. Restart Jenkins when prompted

The plugin auto-configures itself upon installation - no additional configuration required in Jenkins.

## Step 2: Generate an API Token

1. Click your **username** in the top-right corner → **Configure**
2. Scroll down to the **API Token** section
3. Click **Add new Token**
4. Enter a descriptive name (e.g., `claude-code-mcp`)
5. Click **Generate**
6. **Copy the token immediately** - it will not be shown again

## Step 3: Create Base64 Credentials

Open PowerShell and run the following, replacing the placeholders with your actual values:

```powershell
# Set your Jenkins credentials
$username = "your-jenkins-username"
$token = "your-api-token-from-step-2"

# Encode credentials as Base64
$credentials = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${username}:${token}"))

# Display the encoded credentials
Write-Host "Encoded credentials: $credentials"
```

**Save the output** - you'll need this Base64 string in the next step.

## Step 4: Configure Claude Code

Create or update the MCP configuration file. You have two options:

### Option A: Project-Level Configuration (Recommended)

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "jenkins": {
      "type": "sse",
      "url": "http://your-jenkins-url:8080/mcp-server/sse",
      "headers": {
        "Authorization": "Basic YOUR_BASE64_CREDENTIALS_HERE"
      }
    }
  }
}
```

### Option B: User-Level Configuration

Add to `~/.claude/settings.json` (or `%USERPROFILE%\.claude\settings.json` on Windows):

```json
{
  "mcpServers": {
    "jenkins": {
      "type": "sse",
      "url": "http://your-jenkins-url:8080/mcp-server/sse",
      "headers": {
        "Authorization": "Basic YOUR_BASE64_CREDENTIALS_HERE"
      }
    }
  }
}
```

**Replace:**
- `your-jenkins-url:8080` - Your actual Jenkins server URL and port
- `YOUR_BASE64_CREDENTIALS_HERE` - The Base64 encoded credentials from Step 3

## Step 5: Verify the Connection

1. Restart Claude Code (or run `/mcp` to refresh MCP servers)
2. Ask Claude Code to list your Jenkins jobs

If configured correctly, Claude Code will be able to interact with your Jenkins instance.

## Available MCP Endpoints

The plugin exposes three transport options:

| Transport | URL | Description |
|-----------|-----|-------------|
| HTTP Streamable | `<jenkins-url>/mcp-server/mcp` | Standard MCP transport |
| SSE | `<jenkins-url>/mcp-server/sse` | Server-Sent Events (recommended for Claude Code) |
| Message | `<jenkins-url>/mcp-server/message` | Message-based transport |

## Available Tools

Once connected, Claude Code can use these tools:

### Job Management
- `getJob` - Retrieve a Jenkins job by path
- `getJobs` - Get paginated job list sorted by name
- `triggerBuild` - Execute a job with optional parameters

### Build Information
- `getBuild` - Access specific or latest build details
- `updateBuild` - Modify build display name and description
- `getBuildLog` - Retrieve log lines with pagination
- `searchBuildLog` - Search for patterns in build logs

### Source Control
- `getJobScm` - View job's SCM configuration
- `getBuildScm` - Access build's SCM settings
- `getBuildChangeSets` - Obtain change log information

### System Operations
- `whoAmI` - Identify current user
- `getStatus` - Check Jenkins health and readiness status

## Optional: System Properties

These Jenkins system properties can be set for additional configuration:

### Origin Header Validation (disabled by default)

```properties
# Enforce origin header matching Jenkins root URL
io.jenkins.plugins.mcp.server.Endpoint.requireOriginMatch=true

# Make origin header mandatory
io.jenkins.plugins.mcp.server.Endpoint.requireOriginHeader=true
```

### Log Limits

```properties
# Maximum log lines to retrieve (default: 10,000)
io.jenkins.plugins.mcp.server.extensions.BuildLogsExtension.limit.max=10000
```

## Troubleshooting

### 401 Unauthorized

- Verify your API token is correct and hasn't expired
- Re-generate the Base64 credentials and update your configuration
- Ensure your Jenkins user has appropriate permissions

### 404 Not Found

- Confirm the MCP Server plugin is installed
- Verify Jenkins was restarted after plugin installation
- Check that the URL path is correct (`/mcp-server/sse`)

### Connection Refused

- Verify the Jenkins URL and port are correct
- Check firewall rules allow connections from your machine
- Ensure Jenkins is running and accessible

### CORS Errors

If accessing Jenkins across origins, you may need to configure the origin validation system properties mentioned above.

### MCP Server Not Appearing in Claude Code

- Run `/mcp` in Claude Code to refresh the server list
- Check the MCP configuration file syntax (valid JSON)
- Verify the configuration file is in the correct location

## Security Considerations

- **Never commit** your `.mcp.json` file with credentials to version control
- Add `.mcp.json` to your `.gitignore` file
- Use a dedicated Jenkins user with minimal required permissions
- Regularly rotate your API tokens
- Consider using environment variables for credentials in CI/CD environments

## Example: Adding .mcp.json to .gitignore

```gitignore
# MCP configuration with credentials
.mcp.json
```

## References

- [Jenkins MCP Server Plugin](https://plugins.jenkins.io/mcp-server)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
