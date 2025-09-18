# MCP Server Debugging and Testing Knowledge

This document captures the debugging process, root causes, and solutions for MCP server issues encountered during development.

## Problem Summary

The MCP server was failing tests with the following symptoms:

- HTTP server running but MCP endpoints not working properly
- Test script showing "unexpected response format" errors
- Tools not being properly registered or accessible
- Session management issues in HTTP mode

## Root Cause Analysis

### Issue 1: Incorrect FastMCP HTTP Integration

**Problem**: The initial implementation tried to mount FastMCP as a sub-application on FastAPI:

```python
# WRONG APPROACH
app = FastAPI()
mcp_app = mcp.http_app()
app.mount("/mcp", mcp_app)  # This caused 307 redirects and routing issues
```

**Root Cause**: FastMCP's `http_app()` is designed to be the main application, not a mounted sub-app. Mounting it caused routing conflicts and redirect loops.

**Solution**: Use FastMCP as the primary HTTP app and add custom routes:

```python
# CORRECT APPROACH
@mcp.custom_route("/api/health", methods=["GET"])
async def health_check(request):
    # Custom endpoint logic

def create_app():
    return mcp.http_app()  # Use FastMCP as the main app
```

### Issue 2: Incorrect Tool Registration

**Problem**: Tools were not being registered properly:

```python
# WRONG APPROACH
mcp.tool()(add_numbers)  # Double function call syntax
```

**Root Cause**: The registration syntax was incorrect - using the decorator pattern improperly.

**Solution**: Use proper decorator syntax:

```python
# CORRECT APPROACH
@mcp.tool
def add_numbers(numbers: list[float]) -> dict:
    """Add a list of numbers and return the total."""
    # Tool implementation
```

### Issue 3: MCP Protocol Handshake Missing

**Problem**: Test script was sending individual requests without proper MCP initialization sequence.

**Root Cause**: MCP protocol requires a specific handshake:

1. Send `initialize` request
2. Wait for response
3. Send `notifications/initialized` notification
4. Then other requests can be made

**Solution**: Implement proper MCP handshake in tests:

```bash
# Correct MCP handshake sequence
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", ...}'
sleep 0.5
echo '{"jsonrpc": "2.0", "method": "notifications/initialized"}'  # Critical step!
sleep 0.5
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", ...}'
```

### Issue 4: HTTP Session Management Complexity

**Problem**: HTTP tests failing with "Missing session ID" errors.

**Root Cause**: FastMCP's HTTP transport uses MCP's StreamableHTTP protocol, which requires:

- Session management through proper MCP client libraries
- Session state maintenance across requests
- Complex transport-layer handling

**Solution**: Acknowledge the limitation and focus on realistic testing:

- Use stdio mode for comprehensive MCP functionality testing
- Use HTTP mode only for basic connectivity and health checks
- Document that full HTTP MCP testing requires proper MCP client libraries

## Key Learning: How FastMCP Actually Tests

After studying FastMCP's own test suite, I discovered they:

1. **Use Python pytest with MCP clients**: Not bash scripts
2. **Use proper transport implementations**: `StreamableHttpTransport`, `SSETransport`, etc.
3. **Never use raw HTTP calls**: Always use MCP client libraries
4. **Focus on client-server architecture**: `FastMCP.Client` connecting to `FastMCP` servers

Example from FastMCP tests:

```python
@pytest.fixture
def fastmcp_server():
    server = FastMCP("TestServer")

    @server.tool
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    return server
```

## Debugging Methodology

### 1. Start with Stdio Mode

Always test MCP functionality in stdio mode first - it's simpler and reveals protocol-level issues:

```bash
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", ...}' | uv run server --mode stdio
```

### 2. Check Tool Registration

Verify tools are properly registered by checking server initialization logs and using tools/list.

### 3. Understand Transport Differences

- **Stdio**: Direct JSON-RPC over stdin/stdout - simpler for testing
- **HTTP**: Complex session-based protocol requiring proper client libraries

### 4. Use Proper Error Analysis

Look for specific error patterns:

- "Missing session ID" → HTTP session management issue
- "Invalid request parameters" → Protocol handshake issue
- "307 Temporary Redirect" → HTTP routing/mounting issue

## Final Solution Architecture

### Server Structure

```python
from fastmcp import FastMCP

mcp = FastMCP("Server Name")

# Register tools with proper decorator
@mcp.tool
def my_tool(param: str) -> dict:
    return {"result": param}

# Register custom HTTP routes
@mcp.custom_route("/api/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok"})

def create_app():
    return mcp.http_app()  # FastMCP as main app
```

### Test Strategy

1. **HTTP Health Check**: Basic connectivity
2. **HTTP MCP Initialization**: Verify MCP endpoint works
3. **Stdio Comprehensive Testing**: Full MCP functionality
4. **Document HTTP Limitations**: Explain why full HTTP testing needs proper clients

### Test Results

```text
🧪 Testing MCP server at http://localhost:35813

0️⃣ Checking server health...
✅ Health check: Server is healthy

1️⃣ Initializing MCP session...
✅ Initialize: Success

🖥️  Testing MCP functionality via stdio mode...
   ✅ Stdio mode: Tools list working
   ✅ Stdio mode: Tool calling working (1+2+3+4+5=15)
🎉 All tests passed!
```

## Best Practices for MCP Development

1. **Use FastMCP as the main HTTP app**: Don't mount it as a sub-application
2. **Use proper decorator syntax**: `@mcp.tool` not `mcp.tool()(function)`
3. **Implement proper MCP handshake**: Always send `notifications/initialized`
4. **Test stdio mode first**: Simpler protocol for debugging
5. **Use appropriate test tools**: Python clients for HTTP, bash for basic connectivity
6. **Understand transport limitations**: HTTP MCP is complex, requires proper clients

## Common Pitfalls

1. **Mounting FastMCP incorrectly**: Causes routing and redirect issues
2. **Skipping initialized notification**: Breaks MCP protocol handshake
3. **Using wrong tool registration syntax**: Tools won't be properly registered
4. **Expecting simple HTTP testing**: MCP over HTTP requires session management
5. **Not checking server logs**: Often contain crucial error information

## Packaging and Module Structure

### Project Structure Best Practices

When creating an MCP server, the module structure matters for both clarity and build system compatibility:

**Recommended Structure**:

```text
src/
  gmail/           # Domain-specific name (not gmail_mcp)
    __init__.py
    main.py        # Entry point with FastMCP setup
    tools.py       # Tool implementations
    service.py     # Domain service integration
```

**Avoid**:

- Generic names like `src/mcp` (not descriptive)
- Redundant names like `src/gmail_mcp` (MCP is implied)

### pyproject.toml Configuration

**Package Name vs Module Name**:

```toml
[project]
name = "gmail"              # Simple, clear package name
version = "0.1.0"
description = "An MCP server with Gmail tools"

[project.scripts]
gmail = "gmail.main:main"   # Module path matches src/ structure
```

**Key Principles**:

1. **Package name should match the src/ directory**: `name = "gmail"` → `src/gmail/`
2. **Entry point should match module path**: `gmail.main:main` for `src/gmail/main.py`
3. **Use uv_build backend**: Works seamlessly with this structure

### Module Renaming Process

When renaming modules (e.g., `old_module` → `gmail`):

1. **Rename the directory**: `mv src/old_name src/new_name`
2. **Update pyproject.toml**:
   - `name = "new_name"`
   - `scripts.entry = "new_name.main:main"`
3. **Update imports in tests**: `from new_name.main import ...`
4. **Clean and rebuild**: `rm -rf .venv uv.lock && uv sync`

**Common Mistake**: Changing only the entry point without matching the package name to the directory structure. This causes build system confusion.

### uv Build System Expectations

The `uv_build` backend expects:

- Package name in `pyproject.toml` matches `src/` subdirectory
- Entry points reference the actual module path
- Standard Python package structure with `__init__.py` files

**Error Pattern**:

```text
Error: Expected a Python module at: src/old_name/__init__.py
```

**Solution**: Ensure package `name` field matches the actual `src/` directory name.

## Resources

- FastMCP tests use Python pytest with proper MCP clients
- MCP Protocol requires specific handshake sequence
- StreamableHTTP is session-based, not stateless HTTP
- Stdio mode is simpler for functional testing
- Custom routes can be added to FastMCP HTTP apps
- uv build system requires package name consistency with src/ structure
