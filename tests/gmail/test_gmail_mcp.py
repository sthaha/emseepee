# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
Test suite for Gmail MCP Server
NOTE: These tests require Gmail credentials to run properly
"""

from collections.abc import AsyncGenerator

import httpx
import pytest
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.utilities.tests import run_server_in_process

from emseepee.main import mcp


def run_math_server(host: str, port: int, **kwargs) -> None:
    """Run the math MCP server for testing."""
    transport = kwargs.get("transport", "http")

    if transport == "http":
        mcp.run(host=host, port=port, transport="http")
    elif transport == "sse":
        mcp.run(host=host, port=port, transport="sse")
    else:
        mcp.run(host=host, port=port, transport=transport)


@pytest.fixture()
async def http_server() -> AsyncGenerator[str, None]:
    """Start HTTP server and return URL."""
    with run_server_in_process(run_math_server, transport="http") as url:
        yield f"{url}/mcp"


@pytest.fixture()
async def sse_server() -> AsyncGenerator[str, None]:
    """Start SSE server and return URL."""
    with run_server_in_process(run_math_server, transport="sse") as url:
        yield f"{url}/mcp"


class TestGmailMCPServer:
    async def test_discover_mailboxes_tool_registration(self, http_server: str):
        """Test that discover_mailboxes tool is properly registered."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            # List all tools
            tools = await client.list_tools()

            # Find discover_mailboxes tool
            discover_tool = None
            for tool in tools:
                if tool.name == "discover_mailboxes":
                    discover_tool = tool
                    break

            assert (
                discover_tool is not None
            ), "discover_mailboxes tool not found in MCP tools list"

            # Verify the tool has proper description
            assert discover_tool.description is not None
            assert "mailbox" in discover_tool.description.lower()

    async def test_discover_mailboxes_error_handling(self, http_server: str):
        """Test discover_mailboxes handles uninitialized state properly."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            result = await client.call_tool("discover_mailboxes", {})

            # Should not cause MCP protocol error
            assert result.is_error is False
            assert "status" in result.data

            # In test environment without real credentials, expect initialization error
            if result.data["status"] == "error":
                assert "error" in result.data
                error_msg = result.data["error"].lower()
                assert (
                    "not initialized" in error_msg
                    or "manager not initialized" in error_msg
                )

    async def test_discover_mailboxes_with_mock_setup(self, http_server: str, tmp_path):
        """Test discover_mailboxes with a mock mailbox directory setup."""
        # Create a temporary mailbox directory structure
        mailbox_dir = tmp_path / "mailboxes"
        mailbox_dir.mkdir()

        # Create mock mailbox directories with required files
        personal_dir = mailbox_dir / "personal"
        personal_dir.mkdir()
        work_dir = mailbox_dir / "work"
        work_dir.mkdir()

        # Create mock tokens.json files (empty but present)
        (personal_dir / "tokens.json").write_text("{}")
        (work_dir / "tokens.json").write_text("{}")

        # This test verifies the discovery logic, but actual service initialization
        # will still fail without real credentials (which is expected)
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            result = await client.call_tool("discover_mailboxes", {})

            # Should handle the case gracefully even with mock setup
            assert result.is_error is False
            assert "status" in result.data

    async def test_get_unread_emails_multi_mailbox_parameter_validation(
        self, http_server: str
    ):
        """Test get_unread_emails properly validates multi-mailbox parameters."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            # Test with list of mailboxes
            result = await client.call_tool(
                "get_unread_emails", {"max_emails": 1, "mailboxes": ["test1", "test2"]}
            )
            assert result.is_error is False, "Should accept list of mailbox names"

            # Test with empty list (should mean "all")
            result = await client.call_tool(
                "get_unread_emails", {"max_emails": 1, "mailboxes": []}
            )
            assert (
                result.is_error is False
            ), "Should accept empty list for all mailboxes"

            # Test with string "all"
            result = await client.call_tool(
                "get_unread_emails", {"max_emails": 1, "mailboxes": "all"}
            )
            assert result.is_error is False, "Should accept string 'all'"

            # Test backward compatibility (no mailboxes parameter)
            result = await client.call_tool("get_unread_emails", {"max_emails": 1})
            assert result.is_error is False, "Should work without mailboxes parameter"

    async def test_mailbox_management_tools_registration(self, http_server: str):
        """Test that all mailbox management tools are properly registered."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            # Verify all expected mailbox management tools exist
            expected_tools = [
                "discover_mailboxes",
                "list_mailboxes",
                "switch_mailbox",
                "add_mailbox",
                "rename_mailbox",
            ]

            for tool_name in expected_tools:
                assert (
                    tool_name in tool_names
                ), f"{tool_name} not found in registered tools"

            # Verify core email tools exist
            core_tools = [
                "get_unread_emails",
                "send_email",
                "search_emails",
                "list_labels",
            ]

            for tool_name in core_tools:
                assert tool_name in tool_names, f"Core tool {tool_name} not found"

    async def test_error_response_structure(self, http_server: str):
        """Test that error responses have consistent structure."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            # Test with a tool that should fail gracefully
            result = await client.call_tool("get_unread_emails", {"max_emails": 5})

            # Should not cause MCP protocol error
            assert result.is_error is False, "Should not cause MCP protocol error"

            # If it fails (expected in test environment), should have proper error structure
            if "error" in result.data:
                # Error message should be descriptive
                assert isinstance(result.data["error"], str)
                assert len(result.data["error"]) > 0

                # Should indicate the specific problem
                error_msg = result.data["error"].lower()
                expected_errors = [
                    "not initialized",
                    "service not initialized",
                    "manager not initialized",
                    "credentials",
                    "authentication",
                ]

                assert any(
                    expected in error_msg for expected in expected_errors
                ), f"Error message should be descriptive: {result.data['error']}"

    async def test_discover_mailboxes_response_security(self, http_server: str):
        """Test that discover_mailboxes doesn't expose internal paths."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            result = await client.call_tool("discover_mailboxes", {})

            # Should not cause MCP protocol error
            assert result.is_error is False
            assert "status" in result.data

            # Check response structure doesn't expose internal details
            if result.data.get("discovered"):
                for mailbox in result.data["discovered"]:
                    # Should NOT contain path (internal detail)
                    assert (
                        "path" not in mailbox
                    ), f"Response should not expose internal paths: {mailbox}"

                    # Should contain public information only
                    assert "mailbox_id" in mailbox
                    assert "status" in mailbox

                    # If successfully loaded, should have email address (public info)
                    if mailbox["status"] == "loaded":
                        # Email might be "Unknown" if there was an error getting it,
                        # but it should be present
                        assert (
                            "email" in mailbox
                        ), "Successfully loaded mailboxes should have email field"

    # TODO: Focus on HTTP transport only for now
    # @pytest.mark.parametrize("transport_server", ["http_server", "sse_server"])
    # async def test_gmail_tools_both_transports(self, transport_server: str, request):
    #     """Test Gmail tools work on both HTTP and SSE transports."""
    #     server_url = request.getfixturevalue(transport_server)

    #     async with Client(transport=StreamableHttpTransport(server_url)) as client:
    #         result = await client.call_tool("get_unread_emails", {"max_emails": 5})
    #         assert "count" in result.data


class TestMathMCPCustomEndpoints:
    """Test the custom endpoints added to FastMCP."""

    async def test_health_endpoint(self):
        """Test that /api/health endpoint works."""
        from emseepee.main import create_app

        app = create_app()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["mcp_endpoint"] == "/mcp"
            assert "tools_count" in data
            assert "tool_categories" in data

    # NOTE: Raw HTTP testing of MCP endpoints requires proper session management
    # which is complex to set up in unit tests. The MCP functionality is tested
    # via proper MCP clients in the tests above.


class TestMCPToolSchema:
    """Test MCP tool schema definitions."""

    async def test_get_unread_emails_schema_includes_mailboxes_parameter(self):
        """Test that get_unread_emails tool schema includes the mailboxes parameter."""
        # Get tools directly from the FastMCP instance
        tools = await mcp._list_tools()

        # Find get_unread_emails tool
        get_unread_emails_tool = None
        for tool in tools:
            if tool.name == "get_unread_emails":
                get_unread_emails_tool = tool
                break

        assert get_unread_emails_tool is not None, "get_unread_emails tool not found"

        # Check tool description includes mailboxes information
        description = get_unread_emails_tool.description
        assert (
            "mailboxes" in description.lower()
        ), "Tool description should mention mailboxes parameter"
        assert (
            "all" in description.lower()
        ), "Tool description should mention 'all' keyword for mailboxes"
        assert (
            "[]" in description
        ), "Tool description should mention empty list for all mailboxes"

        # Get the tool's input schema
        schema = (
            get_unread_emails_tool.input_schema
            if hasattr(get_unread_emails_tool, "input_schema")
            else getattr(get_unread_emails_tool, "_input_schema", None)
        )

        if schema:
            properties = schema.get("properties", {})

            # Check that mailboxes parameter exists
            assert (
                "mailboxes" in properties
            ), f"mailboxes parameter not found in schema. Available: {list(properties.keys())}"

            # Verify mailboxes parameter schema (now supports Union[str, List[str]])
            mailboxes_schema = properties["mailboxes"]
            # The schema might be a union type or have anyOf for string/array
            schema_type = mailboxes_schema.get("type")
            any_of = mailboxes_schema.get("anyOf", [])

            # Check if it supports string or array types
            supports_string = schema_type == "string" or any(
                item.get("type") == "string" for item in any_of
            )
            supports_array = (
                schema_type == "array"
                or any(item.get("type") == "array" for item in any_of)
                or schema_type is None  # Allow null for backward compatibility
            )

            assert (
                supports_string or supports_array
            ), f"mailboxes should support string or array types. Got: {mailboxes_schema}"

            # Check that it's optional (not in required parameters)
            required_params = schema.get("required", [])
            assert (
                "mailboxes" not in required_params
            ), "mailboxes parameter should be optional"

            # Verify max_emails parameter still exists (backward compatibility)
            assert (
                "max_emails" in properties
            ), "max_emails parameter should still exist for backward compatibility"

    async def test_get_unread_emails_tool_registration(self, http_server: str):
        """Test that get_unread_emails tool is properly registered with mailboxes parameter."""
        async with Client(transport=StreamableHttpTransport(http_server)) as client:
            # List all tools
            tools = await client.list_tools()

            # Find get_unread_emails tool
            get_unread_emails_tool = None
            for tool in tools:
                if tool.name == "get_unread_emails":
                    get_unread_emails_tool = tool
                    break

            assert (
                get_unread_emails_tool is not None
            ), "get_unread_emails tool not found in MCP tools list"

            # Check that description mentions mailboxes functionality
            description = get_unread_emails_tool.description
            assert (
                "mailboxes" in description.lower()
            ), "Tool description should document mailboxes parameter"

            # Verify input schema includes mailboxes parameter
            input_schema = get_unread_emails_tool.inputSchema
            properties = input_schema.get("properties", {})

            assert (
                "mailboxes" in properties
            ), "mailboxes parameter should be in tool's input schema"
            assert "max_emails" in properties, "max_emails parameter should still exist"

            # Test that the tool can be called with mailboxes parameter
            # Note: This will likely fail due to uninitialized service in test environment,
            # but we're testing that the parameter is accepted by the MCP protocol
            try:
                result = await client.call_tool(
                    "get_unread_emails", {"max_emails": 1, "mailboxes": ["test"]}
                )
                # We expect this to fail gracefully with proper error handling
                assert (
                    result.is_error is False
                ), "Tool call should not result in MCP protocol error"
                # The actual result may contain an error due to uninitialized service
                if "error" in result.data:
                    assert (
                        "service not initialized" in result.data["error"].lower()
                        or "manager not initialized" in result.data["error"].lower()
                    )
            except Exception as e:
                # If there's an exception, it should not be due to unknown parameter
                assert (
                    "mailboxes" not in str(e).lower()
                ), f"Tool should accept mailboxes parameter: {e}"

            # Test that the tool accepts string format for mailboxes (new functionality)
            try:
                result = await client.call_tool(
                    "get_unread_emails", {"max_emails": 1, "mailboxes": "all"}
                )
                # We expect this to not fail at the parameter level anymore
                assert (
                    result.is_error is False
                ), "Tool call should accept string 'all' for mailboxes parameter"
            except Exception as e:
                # If there's an exception, it should not be due to schema validation
                assert (
                    "not any of" not in str(e).lower()
                ), f"Tool should now accept string mailboxes parameter: {e}"
