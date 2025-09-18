#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
MCP Server with Gmail tools supporting stdio and streamable HTTP transports.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import List, Optional, Union

import click
from fastmcp import FastMCP

from config import Loader as config

from .gmail import tools
from .gmail.manager import MailboxManager

# Set up logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
mcp = FastMCP("Gmail Server")

# Email Management Tools


@mcp.tool
async def get_unread_emails(
    max_emails: int = 5, mailboxes: Optional[Union[str, List[str]]] = None
) -> dict:
    """Retrieve unread emails from Gmail inbox(es).

    Args:
        max_emails: Maximum number of emails to retrieve (default: 5)
        mailboxes: Mailbox(es) to get emails from. Can be:
                  - None: Uses current mailbox (default)
                  - "all" or []: Gets emails from ALL available mailboxes
                  - ["all"]: Gets emails from ALL available mailboxes
                  - "foo": Gets emails from specific mailbox
                  - ["foo", "bar"]: Gets emails from specific mailboxes

    Returns:
        Dict with count and list of email dictionaries. Each email includes:
        - id, subject, sender, date, snippet: Basic email info
        - labels: Array of label objects with id and name
        - mailbox_id: Which mailbox this email belongs to
    """
    try:
        # Convert string to list for consistency
        mailboxes = mailboxes or []

        if isinstance(mailboxes, str):
            if mailboxes == "all":
                mailboxes = []
            else:
                mailboxes = [mailboxes]  # Single mailbox as list

        logger.info(f"Fetching {max_emails} emails from mailboxes: {mailboxes}")
        emails = await tools.get_unread_emails(max_emails, mailboxes)
        return {"count": len(emails), "emails": emails}

    except Exception as e:
        return {"error": str(e), "count": 0, "emails": []}


@mcp.tool
async def send_email(recipient_id: str, subject: str, message: str) -> dict:
    """Send an email to the specified recipient."""
    try:
        result = await tools.send_email(recipient_id, subject, message)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def read_email(email_id: str) -> dict:
    """Read the full content of an email by ID."""
    try:
        result = await tools.read_email(email_id)
        return {"status": "success", "email": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def trash_email(email_id: str) -> dict:
    """Move an email to trash."""
    try:
        result = await tools.trash_email(email_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def mark_email_as_read(email_id: str) -> dict:
    """Mark an email as read."""
    try:
        result = await tools.mark_email_as_read(email_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def open_email(email_id: str) -> dict:
    """Open an email in the default web browser."""
    try:
        result = await tools.open_email(email_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def archive_email(email_id: str) -> dict:
    """Archive an email (remove from inbox)."""
    try:
        result = await tools.archive_email(email_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def restore_to_inbox(email_id: str) -> dict:
    """Restore an archived email back to inbox."""
    try:
        result = await tools.restore_to_inbox(email_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Draft Management Tools


@mcp.tool
async def create_draft(recipient_id: str, subject: str, message: str) -> dict:
    """Create a new email draft."""
    try:
        result = await tools.create_draft(recipient_id, subject, message)
        return {"status": "success", "draft": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def list_drafts() -> dict:
    """List all draft emails."""
    try:
        result = await tools.list_drafts()
        return {"status": "success", "drafts": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Label Management Tools


@mcp.tool
async def list_labels() -> dict:
    """List all Gmail labels."""
    try:
        result = await tools.list_labels()
        return {"status": "success", "labels": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def create_label(name: str) -> dict:
    """Create a new Gmail label."""
    try:
        result = await tools.create_label(name)
        return {"status": "success", "label": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def apply_label(email_id: str, label_id: str) -> dict:
    """Apply a label to an email."""
    try:
        result = await tools.apply_label(email_id, label_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def remove_label(email_id: str, label_id: str) -> dict:
    """Remove a label from an email."""
    try:
        result = await tools.remove_label(email_id, label_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def rename_label(label_id: str, new_name: str) -> dict:
    """Rename an existing label."""
    try:
        result = await tools.rename_label(label_id, new_name)
        return {"status": "success", "label": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def delete_label(label_id: str) -> dict:
    """Delete a Gmail label."""
    try:
        result = await tools.delete_label(label_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def search_by_label(label_id: str) -> dict:
    """Search for emails with a specific label."""
    try:
        result = await tools.search_by_label(label_id)
        return {"status": "success", "emails": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Filter Management Tools


@mcp.tool
async def list_filters() -> dict:
    """List all Gmail filters."""
    try:
        result = await tools.list_filters()
        return {"status": "success", "filters": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def get_filter(filter_id: str) -> dict:
    """Get details of a specific Gmail filter."""
    try:
        result = await tools.get_filter(filter_id)
        return {"status": "success", "filter": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def create_filter(
    from_email: Optional[str] = None,
    to_email: Optional[str] = None,
    subject: Optional[str] = None,
    query: Optional[str] = None,
    exclude_chats: Optional[bool] = None,
    has_attachment: Optional[bool] = None,
    size: Optional[int] = None,
    size_comparison: Optional[str] = None,
    add_label_ids: Optional[list] = None,
    remove_label_ids: Optional[list] = None,
    forward: Optional[str] = None,
    never_spam: Optional[bool] = None,
) -> dict:
    """Create a new Gmail filter with specified criteria and actions."""
    try:
        result = await tools.create_filter(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            query=query,
            exclude_chats=exclude_chats,
            has_attachment=has_attachment,
            size=size,
            size_comparison=size_comparison,
            add_label_ids=add_label_ids,
            remove_label_ids=remove_label_ids,
            forward=forward,
            never_spam=never_spam,
        )
        return {"status": "success", "filter": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def delete_filter(filter_id: str) -> dict:
    """Delete a Gmail filter."""
    try:
        result = await tools.delete_filter(filter_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Search Tools


@mcp.tool
async def search_emails(query: str, max_results: int = 50) -> dict:
    """Search emails using Gmail's search syntax."""
    try:
        result = await tools.search_emails(query, max_results)
        return {"status": "success", "emails": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Folder/Organization Tools


@mcp.tool
async def create_folder(name: str) -> dict:
    """Create a new folder (implemented as nested label)."""
    try:
        result = await tools.create_folder(name)
        return {"status": "success", "folder": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def move_to_folder(email_id: str, folder_id: str) -> dict:
    """Move an email to a folder."""
    try:
        result = await tools.move_to_folder(email_id, folder_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def list_folders() -> dict:
    """List all folders (nested labels)."""
    try:
        result = await tools.list_folders()
        return {"status": "success", "folders": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Batch Operations


@mcp.tool
async def batch_archive(query: str, max_emails: int = 100) -> dict:
    """Archive multiple emails matching a search query."""
    try:
        result = await tools.batch_archive(query, max_emails)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def list_archived(max_results: int = 50) -> dict:
    """List archived emails."""
    try:
        result = await tools.list_archived(max_results)
        return {"status": "success", "emails": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Mailbox Management Tools


@mcp.tool
async def add_mailbox(mailbox_id: str, creds_file_path: str, tokens_dir: str) -> dict:
    """Add a new Gmail mailbox/account."""
    try:
        result = await tools.add_mailbox(mailbox_id, creds_file_path, tokens_dir)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def switch_mailbox(mailbox_id: str) -> dict:
    """Switch to a different mailbox/account."""
    try:
        result = await tools.switch_mailbox(mailbox_id)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def list_mailboxes() -> dict:
    """List all configured mailboxes/accounts."""
    try:
        result = await tools.list_mailboxes()
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def discover_mailboxes() -> dict:
    """Discover existing mailboxes based on token files."""
    try:
        result = await tools.discover_mailboxes()
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def refresh_tokens(mailbox_id: Optional[str] = None) -> dict:
    """Refresh tokens for a specific mailbox or all mailboxes."""
    try:
        result = await tools.refresh_tokens(mailbox_id)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
async def rename_mailbox(old_mailbox_id: str, new_mailbox_id: str) -> dict:
    """Rename a mailbox by changing its ID and updating the associated token file.

    Args:
        old_mailbox_id: The current mailbox ID to rename
        new_mailbox_id: The new mailbox ID to use

    Returns:
        Dict containing the operation result and details
    """
    try:
        result = await tools.rename_mailbox(old_mailbox_id, new_mailbox_id)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Global variable to track the running server
server_instance = None


# Add custom routes to the MCP server before creating the HTTP app
@mcp.custom_route("/api/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint."""
    from starlette.responses import JSONResponse

    return JSONResponse(
        {
            "status": "ok",
            "message": "emseepee MCP Server is running",
            "mcp_endpoint": "/mcp",
            "tools_count": 32,
            "tool_categories": {
                "email_management": 8,
                "draft_management": 2,
                "label_management": 6,
                "filter_management": 4,
                "search": 1,
                "folder_organization": 3,
                "batch_operations": 2,
                "mailbox_management": 5,
            },
            "features": [
                "Multi-mailbox support",
                "Email sending and reading",
                "Label and filter management",
                "Search and organization",
                "Draft management",
                "Batch operations",
                "Archive management",
            ],
        }
    )


@mcp.custom_route("/api/shutdown", methods=["POST"])
async def shutdown(request):
    """Gracefully shutdown the server."""
    from starlette.responses import JSONResponse

    async def delayed_shutdown():
        # Wait a bit for the response to be sent
        await asyncio.sleep(0.1)
        if server_instance:
            server_instance.should_exit = True
        else:
            # Fallback: send SIGTERM to current process
            os.kill(os.getpid(), signal.SIGTERM)

    # Schedule shutdown after response is sent
    asyncio.create_task(delayed_shutdown())

    return JSONResponse(
        {"status": "shutting_down", "message": "Server shutdown initiated"}
    )


def create_app():
    """Create MCP HTTP app with custom API endpoints."""
    # Get the FastMCP HTTP app - this handles MCP at root by default
    return mcp.http_app()


@click.group()
def cli():
    """emseepee - Model Context Protocol servers with productivity tools."""
    pass


@cli.group()
def gmail():
    """Gmail MCP server commands."""
    pass


@gmail.command()
@click.option(
    "--name", required=True, help="Mailbox name/identifier (e.g., 'personal', 'work')"
)
@click.option("--config-file", help="YAML configuration file path")
@click.option(
    "--credential-file", help="OAuth 2.0 credentials file path (overrides config)"
)
@click.option(
    "--mailbox-dir",
    help="Directory containing mailbox subdirectories (overrides config)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level",
)
def add(
    name: str,
    config_file: Optional[str],
    credential_file: Optional[str],
    mailbox_dir: Optional[str],
    log_level: str,
):
    """Add a new mailbox with OAuth setup.

    This command:
    1. Creates the mailbox directory structure
    2. Initiates OAuth flow for Gmail access
    3. Stores tokens securely
    4. Validates the setup

    Examples:
        # Using config file
        emseepee gmail add --name personal --config-file ~/.gmail-config.yaml

        # Using direct arguments
        emseepee gmail add --name personal --credential-file ~/.creds/gmail/creds.json --mailbox-dir ~/.creds/gmail/mailboxes/

        # Mixing config file with overrides
        emseepee gmail add --name personal --config-file ~/.gmail-config.yaml --mailbox-dir /custom/path
    """
    logging.basicConfig(level=getattr(logging, log_level.upper()))

    try:
        # Load and validate configuration
        gmail_config = config.from_file_and_cli(
            config_file=config_file,
            credential_file=credential_file,
            mailbox_dir=mailbox_dir,
            log_level=log_level,
        )

        from pathlib import Path

        # Initialize manager
        manager = MailboxManager(gmail_config.mailbox_dir, gmail_config.credential_file)

        # Check if mailbox already exists
        mailbox_path = Path(gmail_config.mailbox_dir) / name
        if mailbox_path.exists():
            logger.error(f"Mailbox '{name}' already exists at {mailbox_path}")
            logger.info(f"To reconfigure, remove directory: rm -rf {mailbox_path}")
            sys.exit(1)

        logger.info(f"Creating mailbox '{name}'...")
        logger.info(f"Mailbox directory: {mailbox_path}")
        logger.info(f"Using credentials: {gmail_config.credential_file}")

        # Add the mailbox (triggers OAuth flow)
        result = manager.add(name, gmail_config.credential_file)

        if result["status"] == "success":
            logger.info("✅ Mailbox added successfully!")
            logger.info(f"📁 Location: {result['mailbox_path']}")
            logger.info(
                f"📧 Ready to use with: emseepee gmail serve --config-file {config_file or 'config.yaml'}"
            )
        else:
            logger.error(f"❌ Failed to add mailbox: {result['message']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Failed to add mailbox '{name}': {e}")
        sys.exit(1)


@gmail.command()
@click.option("--config-file", help="YAML configuration file path")
@click.option(
    "--credential-file", help="OAuth 2.0 credentials file path (overrides config)"
)
@click.option(
    "--mailbox-dir",
    help="Directory containing mailbox subdirectories (overrides config)",
)
@click.option(
    "--mode",
    default="http",
    type=click.Choice(["stdio", "http"]),
    help="Transport mode for the MCP server (default: http)",
)
@click.option(
    "--port", default=63417, type=int, help="Port to run the server on (default: 63417)"
)
@click.option(
    "--addr",
    default="localhost",
    type=str,
    help="Address to bind the server to (default: localhost)",
)
@click.option(
    "--mailbox",
    help="Mailbox ID to set as current (optional - if not provided, uses first discovered mailbox)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level",
)
def serve(
    config_file: Optional[str],
    credential_file: Optional[str],
    mailbox_dir: Optional[str],
    mode: str,
    port: int,
    addr: str,
    mailbox: Optional[str],
    log_level: str,
):
    """Start the MCP server (requires existing mailboxes).

    This command:
    1. Discovers existing mailboxes in the mailbox directory
    2. Validates tokens for all mailboxes
    3. Starts the MCP server
    4. Exits with clear error if setup is invalid

    Examples:
        # Using config file
        emseepee gmail serve --config-file ~/.gmail-config.yaml

        # Using direct arguments
        emseepee gmail serve --credential-file ~/.creds/gmail/creds.json --mailbox-dir ~/.creds/gmail/mailboxes/

        # Mixing config file with overrides
        emseepee gmail serve --config-file ~/.gmail-config.yaml --port 8080 --mailbox=work
    """
    global server_instance

    logging.basicConfig(level=getattr(logging, log_level.upper()))

    # Initialize Gmail service with strict validation
    try:
        # Load and validate configuration
        gmail_config = config.from_file_and_cli(
            config_file=config_file,
            credential_file=credential_file,
            mailbox_dir=mailbox_dir,
            mode=(
                mode if mode != "http" else None
            ),  # Only override if changed from default
            port=(
                port if port != 63417 else None
            ),  # Only override if changed from default
            addr=(
                addr if addr != "localhost" else None
            ),  # Only override if changed from default
            mailbox=mailbox,
            log_level=log_level,
        )

        logger.info(f"Discovering mailboxes in: {gmail_config.mailbox_dir}")
        logger.info(f"Using credentials: {gmail_config.credential_file}")

        # Use separate discovery function with fail-fast behavior
        _discover_and_validate_mailboxes(
            gmail_config.credential_file, gmail_config.mailbox_dir, gmail_config.mailbox
        )

        logger.info("✅ All mailboxes validated successfully")
        logger.info(
            f"🚀 Starting MCP server on {gmail_config.addr}:{gmail_config.port} in {gmail_config.mode} mode..."
        )

    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        logger.info(
            "💡 Run 'emseepee gmail add --name <mailbox-name>' to set up mailboxes first"
        )
        sys.exit(1)

    if gmail_config.mode == "stdio":
        # Run in stdio mode
        mcp.run()
    elif gmail_config.mode == "http":
        # Run FastAPI app with MCP server mounted and API endpoints
        import uvicorn

        app = create_app()
        uvicorn_config = uvicorn.Config(
            app, host=gmail_config.addr, port=gmail_config.port
        )
        server_instance = uvicorn.Server(uvicorn_config)
        server_instance.run()


def _discover_and_validate_mailboxes(
    creds_file: str, mailbox_dir: str, requested_mailbox: Optional[str] = None
):
    """Discover and validate mailboxes with fail-fast behavior.

    Args:
        creds_file: Path to OAuth 2.0 credentials file
        mailbox_dir: Directory containing mailbox subdirectories
        requested_mailbox: Optional specific mailbox to set as current

    Raises:
        ValueError: If no valid mailboxes found or requested mailbox invalid
    """
    from pathlib import Path

    # Check if credentials file exists
    creds_path = Path(creds_file)
    if not creds_path.exists():
        raise ValueError(f"Credentials file does not exist: {creds_file}")

    # Check if mailbox directory exists
    mailbox_path = Path(mailbox_dir)
    if not mailbox_path.exists():
        raise ValueError(
            f"Mailbox directory does not exist: {mailbox_dir}\n"
            f"Create mailboxes using: emseepee gmail add --name <mailbox-name> --credential-file {creds_file} --mailbox-dir {mailbox_dir}"
        )

    # Initialize manager for discovery
    manager = MailboxManager(mailbox_dir, creds_file)
    discovery_result = manager.discover()

    if discovery_result["status"] == "error":
        raise ValueError(f"Discovery failed: {discovery_result['message']}")

    # Get successfully loaded mailboxes
    loaded_mailboxes = [
        m["mailbox_id"]
        for m in discovery_result["discovered"]
        if m.get("status") in ["loaded", "active"]
    ]

    if not loaded_mailboxes:
        raise ValueError(
            f"No valid mailboxes found in: {mailbox_dir}\n"
            f"Add mailboxes using: emseepee gmail add --name <mailbox-name> --credential-file {creds_file} --mailbox-dir {mailbox_dir}\n"
            f"Expected directory structure:\n"
            f"  {mailbox_dir}/\n"
            f"    personal/\n"
            f"      tokens.json\n"
            f"      cache/        # (created automatically)\n"
            f"    work/\n"
            f"      tokens.json"
        )

    # Validate requested mailbox if specified
    if requested_mailbox and requested_mailbox not in loaded_mailboxes:
        raise ValueError(
            f"Requested mailbox '{requested_mailbox}' not found.\n"
            f"Available mailboxes: {', '.join(loaded_mailboxes)}\n"
            f"Add it using: emseepee gmail add --name {requested_mailbox} --credential-file {creds_file} --mailbox-dir {mailbox_dir}"
        )

    # Initialize the global service with validated mailboxes
    tools.initialize_gmail_service_with_mailbox_dir(
        creds_file, mailbox_dir, requested_mailbox
    )

    logger.info(
        f"📧 Loaded {len(loaded_mailboxes)} mailboxes: {', '.join(loaded_mailboxes)}"
    )


# Keep legacy main function for backward compatibility during transition
def main():
    """Legacy entry point - redirects to new CLI structure."""
    cli()


if __name__ == "__main__":
    cli()
