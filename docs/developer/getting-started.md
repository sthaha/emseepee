# Getting Started - Developer Guide

This guide will help you set up your development environment and get the Math MCP Server running locally.

## Prerequisites

- **Python 3.12+** - Required for the project
- **uv** - Fast Python package manager and project manager

### Installing uv

If you don't have uv installed, install it first:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip (if you prefer)
pip install uv
```

## Project Setup

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd math-mcp
```

### 2. Install Dependencies

```bash
# Install main dependencies (creates .venv automatically)
uv sync

# Install with test dependencies for development
uv sync --extra test
```

This creates a local `.venv` directory with all dependencies installed.

### 3. Verify Installation

```bash
# Check that the tool can be found
uv run math-mcp --help

# Should show CLI options
```

## Development Workflow

### Running the Server

```bash
# Start the HTTP server (default mode)
uv run math-mcp

# Start with custom port
uv run math-mcp --port 8080

# Start with custom address
uv run math-mcp --addr 0.0.0.0 --port 8080

# Run in stdio mode (for direct MCP client connections)
uv run math-mcp --mode stdio
```

The server will be available at:

- **MCP Endpoint**: `http://localhost:35813/mcp`
- **Health Check**: `http://localhost:35813/api/health`
- **API Documentation**: `http://localhost:35813/docs`

### Running Tests

#### Bash Test Suite

```bash
# Run comprehensive integration tests
tests/test_mcp.sh

# Test with custom port (make sure server is running on that port)
tests/test_mcp.sh --port 8080

# Show help
tests/test_mcp.sh --help
```

#### Python Test Suite

```bash
# Run all Python tests
uv run pytest tests/test_math_mcp.py -v

# Run specific test class
uv run pytest tests/test_math_mcp.py::TestMathMCPServer -v

# Run with coverage
uv run pytest tests/ --cov=math_mcp

# Run all tests in tests directory
uv run pytest tests/
```

### Testing the API

#### Health Check

```bash
curl http://localhost:35813/api/health
```

#### MCP Tool Testing

```bash
# List available tools
curl -X POST http://localhost:35813/mcp \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Call add_numbers tool
curl -X POST http://localhost:35813/mcp \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add_numbers","arguments":{"numbers":[1,2,3,4,5]}}}'
```

#### Graceful Shutdown

```bash
curl -X POST http://localhost:35813/api/shutdown
```

## Development Commands

### Dependency Management

```bash
# Add new dependency
uv add package-name

# Add development dependency
uv add --extra test package-name

# Update dependencies
uv sync

# Show installed packages
uv pip list
```

### Code Quality

```bash
# Format code (if you add formatters)
uv run black src/ tests/

# Lint code (if you add linters)
uv run ruff check src/ tests/

# Type checking (if you add mypy)
uv run mypy src/
```

## Project Structure

```text
math-mcp/
├── src/math_mcp/           # Source code
│   ├── __init__.py         # Package initialization
│   ├── main.py             # CLI and FastAPI server
│   └── tools.py            # MCP tool implementations
├── tests/                  # Test suite
│   ├── test_math_mcp.py    # Python tests
│   └── test_mcp.sh         # Bash integration tests
├── docs/developer/         # Developer documentation
├── pyproject.toml          # Project configuration
└── README.md               # User documentation
```

## Making Changes

### 1. Add a New Tool

1. **Implement the tool** in `src/math_mcp/tools.py`:

   ```python
   def my_new_tool(param: str) -> dict:
       """Tool description."""
       return {"result": f"processed {param}"}
   ```

2. **Register the tool** in `src/math_mcp/main.py`:

   ```python
   from .tools import add_numbers, my_new_tool

   mcp.tool()(add_numbers)
   mcp.tool()(my_new_tool)  # Add this line
   ```

3. **Add tests** in `tests/test_math_mcp.py`

4. **Test your changes**:

   ```bash
   uv run math-mcp  # Start server
   tests/test_mcp.sh  # Run tests
   ```

### 2. Modify Existing Code

1. Make your changes
2. Run tests to ensure nothing breaks
3. Update documentation if needed

## Troubleshooting

### Common Issues

**Import Errors**:

```bash
# Reinstall dependencies
uv sync --reinstall
```

**Server Won't Start**:

```bash
# Check if port is in use
lsof -i :35813

# Try different port
uv run math-mcp --port 8080
```

**Tests Failing**:

```bash
# Ensure server is running before bash tests
uv run math-mcp &  # Start in background
tests/test_mcp.sh  # Run tests
kill %1            # Stop background server
```

**uv Command Not Found**:

- Restart your terminal after installing uv
- Check your PATH includes `~/.local/bin` (Linux/macOS)

### Getting Help

- Check the [main README](../../README.md) for user documentation
- Review existing tests for code examples
- Look at FastMCP documentation for MCP protocol details
- Open an issue if you find bugs or need features

## Next Steps

Once you have the development environment working:

1. Explore the [Developer Documentation Index](./README.md)
2. Read about the [project architecture](./architecture.md) *(coming soon)*
3. Learn how to [add new tools](./adding-tools.md) *(coming soon)*
4. Review [testing best practices](./testing.md) *(coming soon)*

---

## Happy coding! 🚀
