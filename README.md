# emseepee - MCP Productivity Tools

A collection of Model Context Protocol (MCP) servers built with FastMCP that provides
productivity tools including Gmail integration and more. The servers support both stdio
and HTTP transports with multi-mailbox functionality, advanced configuration options,
and comprehensive productivity tools.

> **🚀 First time here?** Jump to the [Getting Started](#-getting-started) section or go directly to the [Complete User Guide](docs/user/README.md) for full setup instructions.

## ⚠️ Personal Project Disclaimer

This project was developed for **personal use and experimentation**. It is provided
**as-is** and may break or not function at all. **Use at your own risk!**

- I may not respond to issues or pull requests
- No warranty or support is provided
- Code quality and functionality are not guaranteed

## 🤖 AI-Generated Codebase

**This entire codebase was generated using [Claude Code](https://claude.ai/code)** as an experiment
to understand how far AI-assisted development can be pushed to create
usable utilities.

**Human contributions were limited to:**

- High-level architecture decisions and requirements
- Multi-mailbox architecture and design patterns
- Configuration system and CLI interface
- Functionality specifications and feature requests
- Minimal hands-on coding or direct code modifications
- Project direction and testing feedback

**Claude Code generated:**

- All source code implementation
- Comprehensive test suite and documentation
- Performance optimizations and security improvements
- Pre-commit hooks and development tooling

This serves as a case study in AI-assisted software development capabilities.

## Attribution / Acknowledgments

This project builds upon and extends the original Gmail MCP Server implementation.
Credit goes to the original author for the foundational Gmail API integration and
MCP tool implementation that helped inspire this project.

See: <https://github.com/theposch/gmail-mcp>

## Features

- **📧 Comprehensive Gmail Tools**:  email management, drafts, labels, filters,
  search, and multi-mailbox support
- **🔄 Multi-Mailbox Support**: Query and manage multiple Gmail accounts simultaneously
- **🚀 Multiple Transports**: stdio and HTTP with streamable responses
- **⚙️ Configuration**: YAML config files with CLI overrides and nested settings
- **🏗️CLI**: Subcommands for setup (`add`) and operations (`serve`)
- **⚡ Performance Optimized**: Concurrent processing, API batching, and persistent caching
- **🧪 Testing**: Python unit tests and bash integration tests

## 🚀 Getting Started

**New to Gmail MCP Server?** Start with our comprehensive setup guide:

### 📖 [Complete User Guide](docs/user/README.md)

The user guide walks you through:

1. **[Google Cloud Setup](docs/user/README.md#1-google-cloud-setup)** - Creating credentials and enabling Gmail API
2. **[Server Setup](docs/user/README.md#2-server-setup)** - Configuration files and mailbox management
3. **[Multi-Mailbox Analysis](docs/user/README.md#multi-mailbox-email-analysis)** - Example prompts for LLM integration
4. **[Troubleshooting](docs/user/README.md#troubleshooting)** - Common issues and solutions

### 👨‍💻 [Developer Documentation](docs/developer/README.md)

For developers wanting to contribute or extend the server:

- **[Getting Started Guide](docs/developer/getting-started.md)** - Development setup and workflow
- **[Architecture Overview](docs/developer/architecture.md)** - System design and patterns

## Quick Start

> ⚠️ **Prerequisites Required**: You need Google Cloud credentials before starting. See the [Complete User Guide](docs/user/README.md#1-google-cloud-setup) for full setup instructions including Google Cloud project creation, Gmail API enablement, and OAuth credentials.

### 1. Installation

```bash
# Install dependencies
uv sync

# Install with test dependencies
uv sync --extra test
```

### 2. Setup Configuration

Create a configuration file to avoid repeating settings:

```bash
# Copy sample configuration
cp hack/config.yaml config.yaml

# Edit with your paths
vim config.yaml
```

**config.yaml example:**

```yaml
# Gmail MCP Server Configuration

# Google Cloud credentials configuration
gcloud:
  # Required: Path to OAuth 2.0 credentials file
  # Can be absolute or relative to this config file
  credential_file: ~/.creds/gmail/creds.json

# Gmail configuration
gmail:
  # Required: Directory containing mailbox subdirectories
  # Can be absolute or relative to this config file
  mailbox_dir: ~/.creds/gmail/mailboxes/

# MCP Server configuration
mcp:
  mode: http            # 'http' or 'stdio'

# HTTP server configuration (only used when mcp.mode = http)
http:
  port: 63417          # Server port
  addr: localhost      # Server address

# Optional: Default mailbox to use
# mailbox: personal
```

### 3. Add Your First Mailbox

```bash
# Using config file (recommended)
emseepee add --name personal --config-file config.yaml

# Using direct arguments
emseepee add \
  --name personal \
  --credential-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/
```

### 4. Start the Server

```bash
# Using config file (recommended)
emseepee gmail serve --config-file config.yaml

# With overrides
emseepee gmail serve \
  --config-file config.yaml \
  --port 8080 \
  --mailbox=personal \
  --log-level=debug

# Server will be available at:
# - MCP endpoint:   http://localhost:63417/mcp
# - API docs:       http://localhost:63417/docs
```

> 📚 **For detailed setup instructions, troubleshooting, and usage examples**: See the [Complete User Guide](docs/user/README.md)

## Command Line Interface

The Gmail MCP Server uses a clean subcommand structure with configuration support.

### Configuration File Support

The server supports YAML configuration files with nested settings and CLI overrides:

- **Nested Structure**: `mcp.mode`, `http.port`, `http.addr`
- **Legacy Support**: Flat structure still supported for backward compatibility
- **CLI Overrides**: Command-line arguments override config file values
- **Path Expansion**: Supports `~` (home directory) and relative paths

### Commands

#### `emseepee gmail add` - Setup and Add Mailboxes

Add new Gmail accounts for multi-mailbox support:

```bash
# Using config file (recommended)
emseepee gmail add --name personal --config-file config.yaml

# Using direct arguments
emseepee gmail add \
  --name personal \
  --credential-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/

# Mixing config file with overrides
emseepee gmail add \
  --name work \
  --config-file config.yaml \
  --mailbox-dir /custom/work/mailboxes/
```

**Options:**

- `--name TEXT`: Mailbox identifier (required)
- `--config-file PATH`: YAML configuration file
- `--credential-file PATH`: OAuth 2.0 credentials file (required if not in config)
- `--mailbox-dir PATH`: Mailbox directory (required if not in config)
- `--log-level [DEBUG|INFO|WARNING|ERROR]`: Logging level

#### `emseepee gmail serve` - Start the Server

Start the MCP server for operations:

```bash
# Using config file (recommended)
emseepee gmail serve --config-file config.yaml

# Using config file with overrides
emseepee gmail serve \
  --config-file config.yaml \
  --port 8080 \
  --mailbox=work \
  --log-level=debug

# Using direct arguments
emseepee gmail serve \
  --credential-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/

# Advanced: stdio mode for direct MCP client connections
emseepee gmail serve \
  --config-file config.yaml \
  --mode stdio \
  --mailbox=personal
```

**Options:**

- `--config-file PATH`: YAML configuration file
- `--credential-file PATH`: OAuth 2.0 credentials file (required if not in config)
- `--mailbox-dir PATH`: Mailbox directory (required if not in config)
- `--mode [http|stdio]`: Transport mode (default: http)
- `--port INTEGER`: Server port (default: 63417)
- `--addr TEXT`: Server address (default: localhost)
- `--mailbox TEXT`: Default mailbox to use
- `--log-level [DEBUG|INFO|WARNING|ERROR]`: Logging level

## Transport Modes

### HTTP Mode (Default)

Runs MCP server with streamable HTTP transport:

```bash
emseepee gmail serve --config-file config.yaml
```

**Available endpoints:**

- **MCP Endpoint**: `http://localhost:63417/mcp`
- **API Docs**: `http://localhost:63417/docs`
- **OpenAPI**: `http://localhost:63417/openapi.json`
- **Health Check**: `http://localhost:63417/api/health`
- **Cache Management**: `http://localhost:63417/api/cache/*`

### Stdio Mode

For direct MCP client connections:

```bash
emseepee gmail serve --config-file config.yaml --mode stdio
```

## Mailbox Directory Structure

The server uses an optimized directory structure for better performance and caching:

```text
~/.creds/gmail/mailboxes/
  personal/
    tokens.json              # OAuth tokens
    settings.json            # Mailbox-specific settings (optional)
    metadata.json            # Last updated timestamps (optional)
    cache/                   # Persistent caches (created automatically)
      labels.json            # Label ID -> name mappings
      profile.json           # User profile information
  work/
    tokens.json
    settings.json
    metadata.json
    cache/
      labels.json
      profile.json
```

## Multi-Mailbox Features

The server supports sophisticated multi-mailbox operations:

### Query Multiple Mailboxes

```python
# Current mailbox only (backward compatible)
emails = get_unread_emails(max_emails=5)

# Specific mailboxes
emails = get_unread_emails(max_emails=5, mailboxes=["personal", "work"])

# ALL mailboxes (two equivalent methods)
emails = get_unread_emails(max_emails=10, mailboxes=[])        # Empty list
emails = get_unread_emails(max_emails=10, mailboxes=["all"])   # Special keyword
```

### Enhanced Response Data

All emails include `mailbox_id` and rich label information:

```json
{
  "mailbox_id": "personal",
  "labels": [
    {"id": "INBOX", "name": "Inbox"},
    {"id": "IMPORTANT", "name": "Important"},
    {"id": "Label_123", "name": "My Custom Label"}
  ]
}
```

## Performance Optimizations

The server includes significant performance improvements:

### Concurrent Processing

- **Multi-Mailbox Queries**: Process multiple mailboxes simultaneously
- **Gmail API Batching**: Fetch email details in batches of 50
- **Persistent Caching**: Label and profile information cached across restarts

### Performance Gains

- **Before**: 3 mailboxes × 5 emails = 15+ sequential API calls (~3-5 seconds)
- **After**: 3 concurrent tasks + batch requests = ~3 API calls total (~0.5-1 second)
- **Result**: 5-10x faster performance

### Cache Management

```bash
# View cache status for all mailboxes
curl http://localhost:63417/api/cache/status

# Clear cache for specific mailbox
curl -X DELETE http://localhost:63417/api/cache/personal

# Clear all caches
curl -X DELETE http://localhost:63417/api/cache/all
```

## Gmail Tools (32 Available)

The server provides Gmail integration:

### Email Management

- `get_unread_emails` - Retrieve unread emails (multi-mailbox support)
- `send_email` - Send emails with attachments
- `read_email` - Get full email content
- `mark_email_as_read/unread` - Update read status
- `delete_email` - Move emails to trash
- `archive_email` - Archive emails

### Multi-Mailbox Operations

- `list_mailboxes` - Show all configured mailboxes
- All tools support mailbox selection or "all mailboxes" operations

### Labels & Organization

- `list_labels` - Get all labels in mailbox
- `add_label_to_email` - Apply labels to emails
- `remove_label_from_email` - Remove labels from emails
- `create_label` - Create new labels
- `delete_label` - Remove labels

### Search & Filters

- `search_emails` - Advanced Gmail search
- `list_filters` - Get email filters
- `create_filter` - Create new filters
- `delete_filter` - Remove filters

### Drafts

- `list_drafts` - Get draft emails
- `create_draft` - Create new drafts
- `update_draft` - Modify existing drafts
- `send_draft` - Send draft emails
- `delete_draft` - Remove drafts

*For complete tool documentation, see the [User Guide](docs/user/README.md).*

## Testing

```bash
# Run Gmail integration tests (requires server running)
tests/gmail/test_mcp.sh

# Run Python unit tests
uv run pytest

# Run specific Gmail test file
uv run pytest tests/gmail/test_gmail_mcp.py -v

# Run config tests
uv run pytest tests/test_config.py -v
```

## Management API

### Health Check

```bash
curl http://localhost:63417/api/health
```

### Graceful Shutdown

```bash
curl -X POST http://localhost:63417/api/shutdown
```

## Troubleshooting

**Server won't start:**

```bash
# Check if port is in use
lsof -i :63417

# Try a different port
emseepee gmail serve --config-file config.yaml --port 8080
```

**Configuration issues:**

```bash
# Validate config file syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Test with direct arguments
emseepee gmail serve \
  --credential-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/
```

**Authentication problems:**

```bash
# Check credentials file exists
ls -la ~/.creds/gmail/creds.json

# Verify mailbox directory structure
ls -la ~/.creds/gmail/mailboxes/
```

For more troubleshooting help, see the [Developer Getting Started Guide](docs/developer/getting-started.md#troubleshooting).

## Documentation

### 📖 [User Guide](docs/user/README.md) - Complete Setup & Usage

Essential for all users:

- **Google Cloud Setup** - Credentials and Gmail API configuration
- **Server Configuration** - YAML config files and multi-mailbox setup
- **LLM Integration Examples** - Ready-to-use prompts for email analysis
- **Multi-Mailbox Operations** - Advanced usage patterns
- **Troubleshooting** - Common issues and solutions

### 👨‍💻 [Developer Documentation](docs/developer/README.md) - Extend & Contribute

For developers and contributors:

- **Getting Started** - Development environment setup
- **Architecture Guide** - System design and patterns
- **Adding Tools** - Extend functionality
- **Testing Strategies** - Unit and integration testing

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file
