# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
Gmail tools for the MCP server.

This module contains comprehensive Gmail functionality including:
- Email management (send, read, trash, archive)
- Draft management (create, list, edit)
- Label management (create, apply, remove, rename, delete)
- Filter management (create, list, view, delete)
- Search functionality
- Folder organization
- Multi-mailbox support
"""

import logging
import time
from typing import List, Dict, Any, Optional

from .manager import MailboxManager

logger = logging.getLogger(__name__)

# Global Gmail service instance and mailbox manager
_gmail_service = None
_mailbox_manager = None


def initialize_gmail_service_with_mailbox_dir(
    creds_file_path: str, mailbox_dir: str, mailbox: Optional[str] = None
):
    """Initialize the Gmail service with mailbox directory structure and optimizations.

    Args:
        creds_file_path: Path to OAuth 2.0 credentials file
        mailbox_dir: Directory containing mailbox subdirectories
        mailbox: Optional specific mailbox to set as current
    """
    global _gmail_service, _mailbox_manager
    from pathlib import Path

    # Initialize enhanced mailbox manager
    _mailbox_manager = MailboxManager(mailbox_dir, creds_file_path)

    # Auto-discover existing mailboxes from directory structure
    discovery_result = _mailbox_manager.discover()

    if discovery_result["status"] == "error":
        raise ValueError(f"Failed to discover mailboxes: {discovery_result['message']}")

    # Get all successfully loaded mailboxes
    loaded_mailboxes = [
        m["mailbox_id"]
        for m in discovery_result["discovered"]
        if m.get("status") in ["loaded", "active"]
    ]

    # Handle case where no mailboxes exist but user specified one to create
    if not loaded_mailboxes and mailbox:
        logger.info(f"No existing mailboxes found. Creating new mailbox: {mailbox}")
        try:
            result = _mailbox_manager.add(mailbox, creds_file_path)
            if result["status"] == "success":
                loaded_mailboxes = [mailbox]
                logger.info(f"Successfully created mailbox: {mailbox}")
            else:
                raise ValueError(f"Failed to create mailbox: {result['message']}")
        except Exception as e:
            raise ValueError(f"Failed to create new mailbox '{mailbox}': {e}")

    if not loaded_mailboxes:
        # No valid mailboxes found and none specified for creation
        mailbox_path = Path(mailbox_dir)
        if not mailbox_path.exists():
            error_msg = (
                f"Mailbox directory does not exist: {mailbox_dir}\n"
                "Create the directory and add mailbox subdirectories with tokens.json files.\n"
                "Example structure:\n"
                f"  {mailbox_dir}/\n"
                "    personal/\n"
                "      tokens.json\n"
                "    work/\n"
                "      tokens.json\n"
                "\n"
                "Or specify --mailbox=<id> to create a new mailbox:\n"
                f"  uv run gmail --mailbox-dir {mailbox_dir} --mailbox=personal --creds-file <path>\n"
                "\n"
                "To migrate from legacy tokens directory, run:\n"
                "  ./migrate_tokens.sh <old-tokens-dir> <new-mailbox-dir>"
            )
        else:
            error_msg = (
                f"No valid Gmail mailboxes found in: {mailbox_dir}\n"
                "Expected structure:\n"
                f"  {mailbox_dir}/\n"
                "    <mailbox-id>/\n"
                "      tokens.json\n"
                "      cache/          # (created automatically)\n"
                "        labels.json\n"
                "        profile.json\n"
                "\n"
                "To create a new mailbox, specify --mailbox=<id>:\n"
                f"  uv run gmail --mailbox-dir {mailbox_dir} --mailbox=personal --creds-file <path>\n"
                "\n"
                "To migrate from legacy tokens directory, run:\n"
                "  ./migrate_tokens.sh <old-tokens-dir> <new-mailbox-dir>"
            )
        raise ValueError(error_msg)

    # Determine which mailbox to use as current
    if mailbox:
        if mailbox not in loaded_mailboxes:
            raise ValueError(
                f"Requested mailbox '{mailbox}' not found. "
                f"Available mailboxes: {', '.join(loaded_mailboxes)}"
            )
        _mailbox_manager.switch(mailbox)
    else:
        # Use the first loaded mailbox as current
        first_mailbox = loaded_mailboxes[0]
        _mailbox_manager.switch(first_mailbox)
        logger.info(f"Using first discovered mailbox as current: {first_mailbox}")

    # Set global service to current mailbox service
    _gmail_service = _mailbox_manager.get_current_service()

    current_mailbox = _mailbox_manager.current_mailbox_id

    logger.info(
        f"Gmail service initialized with {len(loaded_mailboxes)} mailboxes. "
        f"Current: {current_mailbox}"
    )
    logger.info(f"Available mailboxes: {', '.join(loaded_mailboxes)}")
    logger.info(f"Mailbox directory: {mailbox_dir}")


# Email Management Tools


async def get_unread_emails(
    max_emails: int = 5, mailboxes: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Retrieve unread emails from Gmail inbox(es) with optimized batching and caching.

    Args:
        max_emails: Maximum number of emails to retrieve (default: 5)
        mailboxes: List of mailbox IDs to get emails from. Special values:
                  - None: Uses current mailbox (default)
                  - []: Gets emails from ALL available mailboxes
                  - ["all"]: Gets emails from ALL available mailboxes
                  - ["foo", "bar"]: Gets emails from specific mailboxes
                  - "foo": Single mailbox (automatically converted to ["foo"])

    Returns:
        List of email dictionaries with id, subject, sender, date, snippet, labels, and mailbox_id
    """
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    # Convert string to list for backward compatibility

    # Performance tracking
    start_time = time.time()

    try:
        # If no mailboxes specified, use current mailbox
        if mailboxes is None:
            if _gmail_service is None:
                raise ValueError("Gmail service not initialized.")

            logger.info(
                f"Getting up to {max_emails} unread emails from current mailbox"
            )

            result = await _gmail_service.get_unread_emails(max_emails)

            if isinstance(result, str):
                # Error occurred
                logger.error(f"Error retrieving unread emails: {result}")
                return []

            # Add current mailbox_id to each email
            current_mailbox = _mailbox_manager.current_mailbox_id
            for email in result:
                email["mailbox_id"] = current_mailbox

            elapsed = time.time() - start_time
            logger.info(
                f"Retrieved {len(result)} unread emails from current mailbox in {elapsed:.2f}s"
            )
            return result

        # Handle "all mailboxes" cases: empty list or ["all"]
        available_mailboxes = list(_mailbox_manager.mailboxes.keys())
        if mailboxes == [] or mailboxes == ["all"]:
            target_mailboxes = available_mailboxes
            logger.info(
                f"Getting unread emails from ALL {len(target_mailboxes)} mailboxes: {target_mailboxes}"
            )
        else:
            target_mailboxes = mailboxes
            logger.info(
                f"Getting unread emails from specific mailboxes: {target_mailboxes}"
            )

        # Validate mailboxes exist
        valid_mailboxes = []
        for mailbox_id in target_mailboxes:
            if mailbox_id not in available_mailboxes:
                logger.warning(
                    f"Mailbox '{mailbox_id}' not found. Available: {available_mailboxes}"
                )
                continue
            valid_mailboxes.append(mailbox_id)

        if not valid_mailboxes:
            logger.warning("No valid mailboxes found")
            return []

        # Process mailboxes sequentially
        logger.info(f"Processing {len(valid_mailboxes)} mailboxes sequentially")
        all_emails = []
        successful_mailboxes = []

        for mailbox_id in valid_mailboxes:
            try:
                service = _mailbox_manager.mailboxes[mailbox_id]

                logger.info(f"Getting unread emails from mailbox '{mailbox_id}'")

                result = await service.get_unread_emails(max_emails)

                if isinstance(result, str):
                    logger.error(
                        f"Error retrieving emails from mailbox '{mailbox_id}': {result}"
                    )
                    continue

                # Add mailbox_id to each email
                for email in result:
                    email["mailbox_id"] = mailbox_id

                all_emails.extend(result)
                successful_mailboxes.append(mailbox_id)
                logger.info(
                    f"Retrieved {len(result)} unread emails from mailbox '{mailbox_id}'"
                )

            except Exception as e:
                logger.error(f"Failed to get emails from mailbox '{mailbox_id}': {e}")
                continue

        # Sort by date (most recent first) and limit to max_emails
        # Note: Gmail date format varies, so we'll keep original order from each mailbox
        # but limit total results
        if len(all_emails) > max_emails:
            all_emails = all_emails[:max_emails]

        elapsed = time.time() - start_time
        successful_count = len(set(email["mailbox_id"] for email in all_emails))

        if mailboxes == [] or mailboxes == ["all"]:
            logger.info(
                f"Retrieved {len(all_emails)} total unread emails from ALL mailboxes "
                f"({successful_count}/{len(available_mailboxes)} successful) in {elapsed:.2f}s"
            )
        else:
            logger.info(
                f"Retrieved {len(all_emails)} total unread emails from {successful_count} mailboxes "
                f"in {elapsed:.2f}s"
            )

        return all_emails

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"get_unread_emails failed after {elapsed:.2f}s: {e}")
        raise


async def send_email(recipient_id: str, subject: str, message: str) -> str:
    """Send an email to the specified recipient."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.send_email(recipient_id, subject, message)


async def read_email(email_id: str) -> Dict[str, Any]:
    """Read the full content of an email by ID."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.read_email(email_id)


async def trash_email(email_id: str) -> str:
    """Move an email to trash."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.trash_email(email_id)


async def mark_email_as_read(email_id: str) -> str:
    """Mark an email as read."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.mark_email_as_read(email_id)


async def open_email(email_id: str) -> str:
    """Open an email in the default web browser."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.open_email(email_id)


async def archive_email(email_id: str) -> str:
    """Archive an email (remove from inbox)."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.archive_email(email_id)


async def restore_to_inbox(email_id: str) -> str:
    """Restore an archived email back to inbox."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.restore_to_inbox(email_id)


# Draft Management Tools


async def create_draft(recipient_id: str, subject: str, message: str) -> Dict[str, Any]:
    """Create a new email draft."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.create_draft(recipient_id, subject, message)


async def list_drafts() -> List[Dict[str, Any]]:
    """List all draft emails."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.list_drafts()


# Label Management Tools


async def list_labels() -> List[Dict[str, Any]]:
    """List all Gmail labels."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.list_labels()


async def create_label(name: str) -> Dict[str, Any]:
    """Create a new Gmail label."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.create_label(name)


async def apply_label(email_id: str, label_id: str) -> str:
    """Apply a label to an email."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.apply_label(email_id, label_id)


async def remove_label(email_id: str, label_id: str) -> str:
    """Remove a label from an email."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.remove_label(email_id, label_id)


async def rename_label(label_id: str, new_name: str) -> Dict[str, Any]:
    """Rename an existing label."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.rename_label(label_id, new_name)


async def delete_label(label_id: str) -> str:
    """Delete a Gmail label."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.delete_label(label_id)


async def search_by_label(label_id: str) -> List[Dict[str, Any]]:
    """Search for emails with a specific label."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.search_by_label(label_id)


# Filter Management Tools


async def list_filters() -> List[Dict[str, Any]]:
    """List all Gmail filters."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.list_filters()


async def get_filter(filter_id: str) -> Dict[str, Any]:
    """Get details of a specific Gmail filter."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.get_filter(filter_id)


async def create_filter(
    from_email: Optional[str] = None,
    to_email: Optional[str] = None,
    subject: Optional[str] = None,
    query: Optional[str] = None,
    exclude_chats: Optional[bool] = None,
    has_attachment: Optional[bool] = None,
    size: Optional[int] = None,
    size_comparison: Optional[str] = None,
    add_label_ids: Optional[List[str]] = None,
    remove_label_ids: Optional[List[str]] = None,
    forward: Optional[str] = None,
    never_spam: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a new Gmail filter with specified criteria and actions."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.create_filter(
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


async def delete_filter(filter_id: str) -> str:
    """Delete a Gmail filter."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.delete_filter(filter_id)


# Search Tools


async def search_emails(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """Search emails using Gmail's search syntax."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.search_emails(query, max_results)


# Folder/Organization Tools


async def create_folder(name: str) -> Dict[str, Any]:
    """Create a new folder (implemented as nested label)."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.create_folder(name)


async def move_to_folder(email_id: str, folder_id: str) -> str:
    """Move an email to a folder."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.move_to_folder(email_id, folder_id)


async def list_folders() -> List[Dict[str, Any]]:
    """List all folders (nested labels)."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.list_folders()


# Batch Operations


async def batch_archive(query: str, max_emails: int = 100) -> Dict[str, Any]:
    """Archive multiple emails matching a search query."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.batch_archive(query, max_emails)


async def list_archived(max_results: int = 50) -> List[Dict[str, Any]]:
    """List archived emails."""
    if _gmail_service is None:
        raise ValueError("Gmail service not initialized.")

    return await _gmail_service.list_archived(max_results)


# Mailbox Management Tools


async def add_mailbox(
    mailbox_id: str, creds_file_path: str, tokens_dir: str
) -> Dict[str, Any]:
    """Add a new Gmail mailbox/account."""
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    return _mailbox_manager.add(mailbox_id, creds_file_path, tokens_dir)


async def switch_mailbox(mailbox_id: str) -> Dict[str, Any]:
    """Switch to a different mailbox/account."""
    global _gmail_service
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    result = _mailbox_manager.switch(mailbox_id)
    if result["status"] == "success":
        # Update global service reference
        _gmail_service = _mailbox_manager.get_current_service()

    return result


async def list_mailboxes() -> Dict[str, Any]:
    """List all configured mailboxes/accounts."""
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    return _mailbox_manager.list_mailboxes()


async def discover_mailboxes() -> Dict[str, Any]:
    """Discover existing mailboxes based on token files."""
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    return _mailbox_manager.discover()


async def refresh_tokens(mailbox_id: Optional[str] = None) -> Dict[str, Any]:
    """Refresh tokens for a specific mailbox or all mailboxes."""
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    return _mailbox_manager.refresh_tokens(mailbox_id)


async def rename_mailbox(old_mailbox_id: str, new_mailbox_id: str) -> Dict[str, Any]:
    """Rename a mailbox by changing its ID and updating the associated token file.

    Args:
        old_mailbox_id: The current mailbox ID to rename
        new_mailbox_id: The new mailbox ID to use

    Returns:
        Dict containing the operation result and details

    Raises:
        ValueError: If mailbox manager is not initialized
    """
    if _mailbox_manager is None:
        raise ValueError("Mailbox manager not initialized.")

    return _mailbox_manager.rename_mailbox(old_mailbox_id, new_mailbox_id)
