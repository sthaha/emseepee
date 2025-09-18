# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
Mailbox manager with directory structure support.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any

from .mailbox_data import MailboxData
from .service import GmailService

logger = logging.getLogger(__name__)


class MailboxManager:
    """Manages multiple Gmail accounts/mailboxes with directory structure support."""

    def __init__(self, mailbox_dir: str, creds_file_path: str):
        """Initialize mailbox manager.

        Args:
            mailbox_dir: Directory containing mailbox subdirectories
            creds_file_path: Path to OAuth 2.0 credentials file
        """
        self.mailboxes: Dict[str, GmailService] = {}
        self.current_mailbox_id: Optional[str] = None
        self.mailbox_dir = Path(mailbox_dir)
        self.creds_file_path = creds_file_path
        self.mailbox_data_cache = {}  # Cache MailboxData objects

    def discover(self) -> Dict[str, Any]:
        """Discover mailboxes from directory structure.

        Returns:
            Dictionary with discovery results
        """
        try:
            if not self.mailbox_dir.exists():
                return {
                    "status": "error",
                    "message": f"Mailbox directory does not exist: {self.mailbox_dir}",
                    "discovered": [],
                }

            discovered = []
            successful_count = 0

            # Scan for mailbox subdirectories
            subdirs = [item for item in self.mailbox_dir.iterdir() if item.is_dir()]

            # If directory is empty, return success with 0 mailboxes (allows creation)
            if not subdirs:
                logger.info(
                    "Mailbox directory is empty - ready for new mailbox creation"
                )
                return {
                    "status": "success",
                    "message": "Empty mailbox directory - ready for new mailbox creation",
                    "discovered": [],
                }

            for item in subdirs:
                mailbox_id = item.name
                logger.info(f"Discovering mailbox: {mailbox_id}")

                try:
                    # Create MailboxData instance
                    mailbox_data = MailboxData(str(item))
                    self.mailbox_data_cache[mailbox_id] = mailbox_data

                    # Check if tokens file exists
                    tokens_file = mailbox_data.get_tokens_path()
                    if not tokens_file.exists():
                        discovered.append(
                            {
                                "mailbox_id": mailbox_id,
                                "status": "missing_tokens",
                                "message": "No tokens file found",
                                "has_cache": item.joinpath("cache").exists(),
                            }
                        )
                        continue

                    # Try to create Gmail service
                    try:
                        service = GmailService(self.creds_file_path, str(tokens_file))

                        # Store service
                        self.mailboxes[mailbox_id] = service

                        # Get user email address (public information)
                        try:
                            email_address = service._get_user_email()
                        except Exception as email_error:
                            logger.warning(
                                f"Could not get email for {mailbox_id}: {email_error}"
                            )
                            email_address = "Unknown"

                        discovered.append(
                            {
                                "mailbox_id": mailbox_id,
                                "status": "loaded",
                                "message": "Successfully loaded",
                                "email": email_address,
                                "has_cache": item.joinpath("cache").exists(),
                            }
                        )
                        successful_count += 1

                    except Exception as service_error:
                        logger.warning(
                            f"Failed to create service for {mailbox_id}: {service_error}"
                        )
                        discovered.append(
                            {
                                "mailbox_id": mailbox_id,
                                "status": "service_error",
                                "message": str(service_error),
                                "has_cache": item.joinpath("cache").exists(),
                            }
                        )

                except Exception as e:
                    logger.error(f"Failed to process mailbox {mailbox_id}: {e}")
                    discovered.append(
                        {
                            "mailbox_id": mailbox_id,
                            "status": "error",
                            "message": str(e),
                            "has_cache": False,
                        }
                    )

            # Return success even if no valid mailboxes (discovery completed)
            if successful_count == 0:
                logger.info("Discovery completed but no valid mailboxes found")
                return {
                    "status": "success",
                    "message": "Discovery completed - no valid mailboxes found but ready for creation",
                    "discovered": discovered,
                }

            logger.info(f"Successfully discovered {successful_count} mailboxes")
            return {
                "status": "success",
                "message": f"Discovered {successful_count} valid mailboxes",
                "discovered": discovered,
            }

        except Exception as e:
            logger.error(f"Failed to discover mailboxes: {e}")
            return {"status": "error", "message": str(e), "discovered": []}

    def add(
        self, mailbox_id: str, creds_file_path: str, tokens_dir: str = None
    ) -> Dict[str, Any]:
        """Add a new mailbox with the new directory structure.

        Args:
            mailbox_id: The mailbox identifier
            creds_file_path: Path to OAuth 2.0 credentials file
            tokens_dir: Ignored - included for compatibility with old interface

        Returns:
            Dictionary with operation result
        """
        try:
            # Create mailbox directory structure
            mailbox_path = self.mailbox_dir / mailbox_id
            mailbox_data = MailboxData(str(mailbox_path))

            # Create Gmail service (this will trigger OAuth flow if needed)
            service = GmailService(creds_file_path, str(mailbox_data.get_tokens_path()))

            # Store service
            self.mailboxes[mailbox_id] = service
            self.mailbox_data_cache[mailbox_id] = mailbox_data

            # Set as current if it's the first one
            if self.current_mailbox_id is None:
                self.current_mailbox_id = mailbox_id

            logger.info(f"Added mailbox '{mailbox_id}' with new directory structure")
            return {
                "status": "success",
                "message": f"Mailbox '{mailbox_id}' added successfully",
                "current_mailbox": self.current_mailbox_id,
                "total_mailboxes": len(self.mailboxes),
                "mailbox_path": str(mailbox_path),
            }

        except Exception as e:
            logger.error(f"Failed to add mailbox '{mailbox_id}': {e}")
            return {"status": "error", "message": f"Failed to add mailbox: {str(e)}"}

    def switch(self, mailbox_id: str) -> bool:
        """Switch to a different mailbox.

        Args:
            mailbox_id: The mailbox to switch to

        Returns:
            True if successful, False otherwise
        """
        if mailbox_id in self.mailboxes:
            self.current_mailbox_id = mailbox_id
            logger.info(f"Switched to mailbox: {mailbox_id}")
            return True
        else:
            logger.warning(f"Mailbox '{mailbox_id}' not found")
            return False

    def get_current_service(self) -> Optional[GmailService]:
        """Get the Gmail service for the current mailbox.

        Returns:
            GmailService instance or None if no current mailbox
        """
        if self.current_mailbox_id and self.current_mailbox_id in self.mailboxes:
            return self.mailboxes[self.current_mailbox_id]
        return None

    def get_data(self, mailbox_id: str) -> Optional[MailboxData]:
        """Get MailboxData instance for a specific mailbox.

        Args:
            mailbox_id: The mailbox identifier

        Returns:
            MailboxData instance or None if not found
        """
        return self.mailbox_data_cache.get(mailbox_id)

    def clear_all_caches(self):
        """Clear all persistent caches for all mailboxes."""
        logger.info("Clearing all mailbox caches")

        for mailbox_id, mailbox_data in self.mailbox_data_cache.items():
            try:
                mailbox_data.clear_caches()
                logger.info(f"Cleared cache for mailbox: {mailbox_id}")
            except Exception as e:
                logger.error(f"Failed to clear cache for {mailbox_id}: {e}")

    def refresh_cache(self, mailbox_id: str):
        """Refresh cache for a specific mailbox.

        Args:
            mailbox_id: The mailbox to refresh
        """
        mailbox_data = self.get_data(mailbox_id)
        if mailbox_data:
            logger.info(f"Refreshing cache for mailbox: {mailbox_id}")
            mailbox_data.clear_caches()
        else:
            logger.warning(f"Mailbox not found for cache refresh: {mailbox_id}")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status for all mailboxes.

        Returns:
            Dictionary with cache information for each mailbox
        """
        status = {}

        for mailbox_id, mailbox_data in self.mailbox_data_cache.items():
            cache_dir = mailbox_data.cache_dir

            status[mailbox_id] = {
                "cache_dir": str(cache_dir),
                "cache_exists": cache_dir.exists(),
                "files": {},
            }

            if cache_dir.exists():
                for cache_file in ["labels.json", "profile.json"]:
                    file_path = cache_dir / cache_file
                    status[mailbox_id]["files"][cache_file] = {
                        "exists": file_path.exists(),
                        "size": file_path.stat().st_size if file_path.exists() else 0,
                        "modified": file_path.stat().st_mtime
                        if file_path.exists()
                        else None,
                    }

        return status

    @classmethod
    def migrate_from_legacy(
        cls, tokens_dir: str, mailbox_dir: str, creds_file_path: str
    ) -> "MailboxManager":
        """Migrate from legacy tokens directory to new mailbox directory structure.

        Args:
            tokens_dir: Path to legacy tokens directory
            mailbox_dir: Path to new mailbox directory
            creds_file_path: Path to credentials file

        Returns:
            New MailboxManager instance
        """
        logger.info(f"Migrating from {tokens_dir} to {mailbox_dir}")

        # Use MailboxData migration utility
        MailboxData.migrate_from_tokens_dir(tokens_dir, mailbox_dir)

        # Create new manager
        manager = cls(mailbox_dir, creds_file_path)

        # Discover the migrated mailboxes
        discovery_result = manager.discover()

        if discovery_result["status"] == "success":
            logger.info(
                f"Migration completed successfully. Discovered {len(manager.mailboxes)} mailboxes."
            )
        else:
            logger.warning(
                f"Migration completed with issues: {discovery_result['message']}"
            )

        return manager
