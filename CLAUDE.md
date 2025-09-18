# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### CLI Commands

The Gmail MCP Server supports both configuration files and direct CLI arguments, with CLI arguments taking precedence for overrides.

#### Configuration File Support

Create a `config.yaml` file to avoid repeating common settings (see `hack/config.yaml` for example):

```yaml
# Gmail MCP Server Configuration

# Required: Path to OAuth 2.0 credentials file
creds_file: ~/.creds/gmail/creds.json

# Required: Directory containing mailbox subdirectories
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

#### Adding Mailboxes (Setup)

```bash
# Using config file (recommended)
emseepee gmail add --name personal --config-file config.yaml

# Using direct arguments
emseepee gmail add \
  --name personal \
  --creds-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/

# Mixing config file with overrides
emseepee gmail add \
  --name work \
  --config-file config.yaml \
  --mailbox-dir /custom/work/mailboxes/
```

#### Running the Server (Operations)

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
  --creds-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/

# Advanced: stdio mode with specific mailbox
emseepee gmail serve \
  --config-file config.yaml \
  --mode stdio \
  --mailbox=personal
```

### Mailbox Directory Structure

The server now uses an optimized directory structure for better performance and caching:

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

### Migration from Legacy Structure

If you have an existing installation with `--tokens-dir`, use the migration script:

```bash
# Migrate from old structure to new structure
./migrate_tokens.sh ~/.creds/gmail/tokens/ ~/.creds/gmail/mailboxes/

# Verify migration
ls -la ~/.creds/gmail/mailboxes/

# Use new structure
uv run emseepee gmail serve \
  --creds-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/ \
  --mailbox=personal
```

### Testing

```bash
# Run comprehensive integration tests (requires server running)
tests/gmail/test_mcp.sh

# Run Python unit tests
uv run pytest tests/

# Run specific Gmail tests
uv run pytest tests/gmail/ -v

# Run specific test file
uv run pytest tests/gmail/test_gmail_mcp.py -v
```

**NOTE**: Python unit tests are working correctly. The async configuration is
properly set with `asyncio_mode = "auto"` in pyproject.toml. Integration tests
in `tests/gmail/test_mcp.sh` may show stdio mode failures when run with invalid
credentials, which is expected behavior due to improved validation logic.

### Server Management

When starting servers for testing or development:

```bash
# Start server in background for testing
uv run emseepee gmail serve \
  --creds-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/ \
  --mailbox=personal \
  --log-level=debug \
  --port 8081 &

# Always gracefully shutdown when done
curl -X POST http://localhost:8081/api/shutdown

# Or use Ctrl+C if running in foreground
```

**IMPORTANT**: Always properly terminate background server processes to avoid:

- Port conflicts with subsequent runs
- Resource leaks and zombie processes
- OAuth token refresh issues

**Available shutdown methods:**

1. **Graceful shutdown**: `POST /api/shutdown` - Cleanly stops the server
2. **Process termination**: `Ctrl+C` (foreground) or `kill <PID>` (background)
3. **Claude Code background tasks**: Use `KillShell` tool for background bash processes

### Development Setup

```bash
# Install dependencies
uv sync

# Install with test dependencies
uv sync --extra test
```

## Performance Optimizations

The server now includes significant performance improvements:

### Batching and Concurrent Processing

- **Concurrent Mailbox Processing**: Multiple mailboxes are queried simultaneously using `asyncio.gather()`
- **Gmail API Batching**: Email details are fetched in batches of 50 (Gmail API best practice)
- **Label Caching**: Label names are cached persistently to avoid repeated API calls

### Performance Improvements

**Before Optimization:**

- 3 mailboxes × 5 emails = 15+ sequential API calls
- Total time: ~3-5 seconds
- Fresh label lookups on every restart

**After Optimization:**

- 3 concurrent mailbox tasks + batch requests = ~3 API calls total
- Total time: ~0.5-1 second (**5-10x faster**)
- Persistent label cache survives restarts

### Cache Management

The persistent cache system stores frequently accessed data:

```bash
# View cache status for all mailboxes
curl http://localhost:63417/api/cache/status

# Clear cache for specific mailbox
curl -X DELETE http://localhost:63417/api/cache/personal

# Clear all caches
curl -X DELETE http://localhost:63417/api/cache/all
```

## Architecture

This is a **Model Context Protocol (MCP) server** built with FastMCP that
provides Gmail integration tools. The architecture follows a modular design:

### Core Components

- **`src/emseepee/main.py`**: FastAPI application and CLI entry point. Creates MCP
  server instance, registers tools, and handles both stdio and HTTP transport modes
- **`src/emseepee/gmail/tools.py`**: Comprehensive MCP tool implementations (32 Gmail
  tools covering email management, drafts, labels, filters, search, and
  multi-mailbox support)
- **`src/emseepee/gmail/service.py`**: Gmail API service wrapper for authentication and
  email operations
- **`src/emseepee/gmail/manager.py`**: Multi-mailbox management logic
- **`src/emseepee/gmail/mailbox_data.py`**: Mailbox data structures
- **Transport Modes**: Supports both stdio (for direct MCP client connections)
  and HTTP with streamable responses

### MCP Integration

The server implements the full MCP protocol:

- Uses FastMCP framework for protocol handling
- Tools are registered via `mcp.tool()` decorator in main.py
- Supports JSON-RPC 2.0 with proper error handling
- HTTP mode serves MCP at `/mcp` endpoint with management API at `/api/*`

### Key Patterns

- **Tool Registration**: Tools are defined in `tools.py` and registered
  in `main.py` using `mcp.tool()(function_name)`
- **Transport Abstraction**: Single codebase supports both stdio
  and HTTP modes via FastMCP
- **Testing Strategy**: Dual approach with Python unit tests and bash
  integration tests that exercise the full HTTP/MCP stack

### Adding New Tools

1. Implement function in `src/emseepee/gmail/tools.py` with proper type hints and docstring
2. Import and register in `src/emseepee/main.py` using `mcp.tool()` decorator
3. Add tests in `tests/gmail/test_gmail_mcp.py`
4. Update health check endpoint tools list in main.py if needed

The server automatically exposes registered tools via the MCP protocol without
additional configuration.

### Testing Requirements

**IMPORTANT**: Always update/add tests when making code changes. This project uses a dual testing approach:

1. **Python Unit Tests** (`tests/gmail/`):
   - Add tests for new functions and tools
   - Test both success and error cases
   - Mock external dependencies (Gmail API calls)
   - Run with: `uv run pytest tests/gmail/ -v`

2. **Integration Tests** (`tests/gmail/test_mcp.sh`):
   - Test full MCP protocol integration
   - Verify tools are properly registered and callable
   - Run with: `tests/gmail/test_mcp.sh` (requires server running)

When modifying existing functionality:

- Update existing test cases to reflect changes
- Add new test cases for new behavior
- Ensure all tests pass before committing
- Consider edge cases and error scenarios

## Code Style and Naming Conventions

### Avoid Naming Stuttering

To maintain clean, readable code, avoid redundant prefixes in module and class names:

**✅ Good Examples:**

- `from .service import GmailService` (not `from .gmail_service import GmailService`)
- `from .manager import MailboxManager` (not `from .mailbox_manager import MailboxManager`)
- Class names: `GmailService`, `MailboxManager` (context provided by module)
- Tool names: `get_unread_emails`, `send_email` (not `get_unread_emails_tool`)

**❌ Avoid:**

- `gmail_service.py` → use `service.py` (context is already `gmail/`)
- `mailbox_manager.py` → use `manager.py` (context is already `gmail/`)
- Tool suffixes like `_tool` (redundant since they're in a tools module)

### Module Organization

- **`main.py`**: Application entry point and CLI interface
- **`gmail/service.py`**: Core Gmail API integration
- **`gmail/manager.py`**: Multi-mailbox management logic
- **`gmail/tools.py`**: MCP tool implementations
- **`gmail/mailbox_data.py`**: Mailbox data structures

This structure avoids redundancy while maintaining clarity through contextual organization.

## Development Patterns and Lessons Learned

### Systematic Code Improvements

When making any improvement to the codebase, always apply it systematically across all similar patterns:

### Best Practice: Search and Apply Consistently

```bash
# 1. Make the improvement to the immediate issue
# 2. Search for similar patterns across the codebase
grep -r "similar_pattern" src/ tests/
# or use MCP tools:
# mcp__serena__search_for_pattern with appropriate regex

# 3. Apply the same improvement consistently
# 4. Update tests and documentation accordingly
```

**Examples of Systematic Improvements:**

- **Schema Type Issues**: If fixing `Optional[List[str]]` → `Union[str, List[str]]` for one tool parameter, check all similar parameters
- **Test Cleanup**: If removing unnecessary `pytest.main()` from one test file, check all test files
- **Import Optimization**: If updating imports in one module, check for similar patterns in related modules
- **Error Handling**: If improving error handling in one function, apply similar improvements to related functions

**Key Principle:** Every improvement is an opportunity to improve the entire codebase, not just the immediate issue. This prevents:

- Inconsistent patterns across the codebase
- Future similar issues
- Technical debt accumulation
- Maintenance overhead

**Search Patterns to Check:**

- Similar function signatures: `grep -r "Optional\[List\[str\]\]" src/`
- Test patterns: `find tests/ -name "*.py" -exec grep -l "pytest.main" {} \;`
- Import patterns: `grep -r "from.*import" src/`
- Error handling: `grep -r "except.*:" src/`

### Multi-Mailbox Tool Design

When extending tools to support multiple mailboxes, follow this pattern:

**✅ Backward Compatible Design with "All Mailboxes" Support:**

```python
async def get_unread_emails(max_emails: int = 5, mailboxes: Optional[List[str]] = None):
    # If no mailboxes specified, use current mailbox (backward compatible)
    if mailboxes is None:
        # Use existing single-mailbox logic
        result = await _gmail_service.get_unread_emails(max_emails)
        # Add mailbox_id to maintain consistency
        for email in result:
            email["mailbox_id"] = _mailbox_manager.current_mailbox_id
        return result

    # Handle "all mailboxes" cases: empty list or ["all"]
    available_mailboxes = list(_mailbox_manager.mailboxes.keys())
    if mailboxes == [] or mailboxes == ["all"]:
        target_mailboxes = available_mailboxes
        logger.info(f"Getting emails from ALL {len(target_mailboxes)} mailboxes")
    else:
        target_mailboxes = mailboxes

    # Handle multiple mailboxes
    all_emails = []
    for mailbox_id in target_mailboxes:
        service = _mailbox_manager.mailboxes[mailbox_id]
        result = await service.get_unread_emails(max_emails)
        # Add mailbox_id to each email
        for email in result:
            email["mailbox_id"] = mailbox_id
        all_emails.extend(result)
    return all_emails
```

**Key Principles:**

- Always maintain backward compatibility when adding optional parameters
- Support "all mailboxes" via empty list `[]` or special keyword `["all"]`
- Consistently add `mailbox_id` field to responses across all mailboxes
- Gracefully handle missing mailboxes with logging, don't fail entirely
- Use the existing `_mailbox_manager.mailboxes` dictionary for direct service access

**Usage Examples:**

```python
# Current mailbox (backward compatible)
emails = await get_unread_emails(max_emails=5)

# Specific mailboxes
emails = await get_unread_emails(max_emails=5, mailboxes=["foo", "bar"])

# ALL mailboxes (two equivalent methods)
emails = await get_unread_emails(max_emails=10, mailboxes=[])        # Empty list
emails = await get_unread_emails(max_emails=10, mailboxes=["all"])   # Special keyword

# Each email includes:
# - mailbox_id: "foo" (identifies source mailbox)
# - labels: [{"id": "INBOX", "name": "Inbox"}, ...]
```

### Gmail API Response Enhancement

When enhancing API responses with additional data (like labels):

**✅ Robust Label Handling:**

```python
# Extract label information with fallback handling
label_ids = msg.get("labelIds", [])
labels = []

for label_id in label_ids:
    try:
        # Handle system labels with known mappings
        if label_id in ["INBOX", "UNREAD", "IMPORTANT", ...]:
            labels.append({
                "id": label_id,
                "name": label_id.replace("CATEGORY_", "").title()
            })
        else:
            # Fetch custom label details from API
            label_response = service.users().labels().get(userId=user_id, id=label_id).execute()
            labels.append({
                "id": label_id,
                "name": label_response.get("name", label_id)
            })
    except Exception as e:
        # Graceful degradation - include ID even if name lookup fails
        logger.warning(f"Could not get label details for {label_id}: {e}")
        labels.append({"id": label_id, "name": label_id})

email_data["labels"] = labels
```

**Key Lessons:**

- Always include both `id` and `name` for consistency and flexibility
- Implement graceful degradation when external API calls fail
- Use logging for debugging without breaking functionality
- Handle system labels separately from custom labels for efficiency

### Testing Multi-Service Features

**Direct Testing Approach:**
When testing complex multi-service features, create direct test scripts that bypass MCP protocol complexities:

```python
# Initialize service with real credentials for integration testing
initialize_gmail_service(creds_file, tokens_dir, mailbox)

# Test various scenarios
current_emails = await get_unread_emails(max_emails=2)  # Current mailbox
multi_emails = await get_unread_emails(max_emails=3, mailboxes=["foo", "bar"])  # Multiple
single_emails = await get_unread_emails(max_emails=2, mailboxes=["foo"])  # Specific

# Verify consistency
assert all("mailbox_id" in email for email in current_emails)
assert all("labels" in email for email in current_emails)
```

**Benefits:**

- Faster iteration during development
- Easier debugging of business logic vs protocol issues
- Can validate real API responses without mocking

### Error Handling in Multi-Mailbox Operations

**✅ Fail-Safe Pattern:**

```python
for mailbox_id in mailboxes:
    if mailbox_id not in available_mailboxes:
        logger.warning(f"Mailbox '{mailbox_id}' not found. Available: {available_mailboxes}")
        continue  # Skip invalid mailboxes, don't fail entire operation

    try:
        # Process mailbox
        service = _mailbox_manager.mailboxes[mailbox_id]
        result = await service.get_unread_emails(max_emails)
        all_emails.extend(result)
    except Exception as e:
        logger.error(f"Failed to get emails from mailbox '{mailbox_id}': {e}")
        continue  # Continue with other mailboxes
```

**Key Insight:** In multi-resource operations, partial success is often better than complete failure. Log issues but continue processing other resources.

### Development Workflow Best Practices

**✅ Background Server Management:**
When testing new features that require a running server:

```bash
# 1. Start server in background with custom port to avoid conflicts
uv run emseepee gmail serve --creds-file ~/.creds/gmail/creds.json --mailbox-dir ./tmp/mailboxes/ --mailbox=test --port 8081 &
GMAIL_PID=$!

# 2. Test your functionality
python test_direct.py

# 3. Always cleanup when done (choose one method):
# Option A: Graceful shutdown via API
curl -X POST http://localhost:8081/api/shutdown

# Option B: Kill the process
kill $GMAIL_PID

# Option C: If using Claude Code background tasks
# Use KillShell tool with the shell ID
```

**Key Principles:**

- Always use custom ports (not default) to avoid conflicts
- Store process IDs when starting background tasks
- Prefer graceful shutdown (`/api/shutdown`) over process termination
- Clean up temporary test files after development
- Use `uv run pytest tests/ -v` for regression testing after changes

**Common Pitfalls to Avoid:**

- Leaving background servers running indefinitely
- Not testing backward compatibility when adding optional parameters
- Forgetting to update existing tests when modifying function signatures
- Starting multiple servers on the same port without checking for conflicts
