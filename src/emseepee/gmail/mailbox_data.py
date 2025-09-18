# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
Mailbox data management for persistent caching and organization.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class MailboxData:
    """Manages persistent data storage for a single Gmail mailbox."""

    CACHE_TTL_HOURS = 24  # Cache labels for 24 hours

    def __init__(self, mailbox_path: str):
        """Initialize mailbox data manager.

        Args:
            mailbox_path: Path to the mailbox directory
        """
        self.mailbox_path = Path(mailbox_path)
        self.cache_dir = self.mailbox_path / "cache"
        self.tokens_file = self.mailbox_path / "tokens.json"
        self.labels_file = self.cache_dir / "labels.json"
        self.profile_file = self.cache_dir / "profile.json"
        self.settings_file = self.mailbox_path / "settings.json"
        self.metadata_file = self.mailbox_path / "metadata.json"

        # Ensure directories exist
        self.mailbox_path.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _is_cache_fresh(
        self, timestamp: Optional[float], ttl_hours: float = CACHE_TTL_HOURS
    ) -> bool:
        """Check if cached data is still fresh."""
        if timestamp is None:
            return False

        age_hours = (time.time() - timestamp) / 3600
        return age_hours < ttl_hours

    def load_labels_cache(self) -> Dict[str, str]:
        """Load cached label ID -> name mappings.

        Returns:
            Dictionary of label_id -> label_name, empty if cache is stale/missing
        """
        if not self.labels_file.exists():
            logger.debug(f"Labels cache file not found: {self.labels_file}")
            return {}

        try:
            with open(self.labels_file) as f:
                cache_data = json.load(f)

            # Check if cache is still fresh
            if self._is_cache_fresh(cache_data.get("timestamp")):
                logger.info(
                    f"Loaded {len(cache_data.get('labels', {}))} labels from cache"
                )
                return cache_data.get("labels", {})
            else:
                logger.info("Labels cache expired, will refresh from API")
                return {}

        except Exception as e:
            logger.warning(f"Failed to load labels cache: {e}")
            return {}

    def save_labels_cache(self, labels: Dict[str, str]):
        """Save label mappings to persistent cache.

        Args:
            labels: Dictionary of label_id -> label_name to cache
        """
        try:
            cache_data = {"timestamp": time.time(), "version": "1.0", "labels": labels}

            # Write atomically using temporary file
            temp_file = self.labels_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            # Atomic move
            temp_file.replace(self.labels_file)
            logger.info(f"Cached {len(labels)} labels to {self.labels_file}")

        except Exception as e:
            logger.error(f"Failed to save labels cache: {e}")

    def load_profile_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached user profile information."""
        if not self.profile_file.exists():
            return None

        try:
            with open(self.profile_file) as f:
                cache_data = json.load(f)

            if self._is_cache_fresh(cache_data.get("timestamp")):
                return cache_data.get("profile")

        except Exception as e:
            logger.warning(f"Failed to load profile cache: {e}")

        return None

    def save_profile_cache(self, profile: Dict[str, Any]):
        """Save user profile to persistent cache."""
        try:
            cache_data = {
                "timestamp": time.time(),
                "version": "1.0",
                "profile": profile,
            }

            with open(self.profile_file, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save profile cache: {e}")

    def get_tokens_path(self) -> Path:
        """Get path to OAuth tokens file."""
        return self.tokens_file

    def clear_caches(self):
        """Clear all cached data (useful for debugging or forced refresh)."""
        for cache_file in [self.labels_file, self.profile_file]:
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    logger.info(f"Cleared cache: {cache_file}")
                except Exception as e:
                    logger.error(f"Failed to clear cache {cache_file}: {e}")

    @classmethod
    def migrate_from_tokens_dir(
        cls, tokens_dir: str, mailbox_dir: str
    ) -> Dict[str, "MailboxData"]:
        """Migrate from legacy tokens directory to new mailbox directory structure.

        Args:
            tokens_dir: Path to legacy tokens directory
            mailbox_dir: Path to new mailbox directory

        Returns:
            Dictionary of mailbox_id -> MailboxData objects
        """
        tokens_path = Path(tokens_dir)
        mailbox_path = Path(mailbox_dir)

        if not tokens_path.exists():
            raise ValueError(f"Tokens directory does not exist: {tokens_dir}")

        mailboxes = {}

        # Find all token files matching pattern: {mailbox_id}-tokens.json
        for token_file in tokens_path.glob("*-tokens.json"):
            mailbox_id = token_file.stem.replace("-tokens", "")

            # Create new mailbox directory
            new_mailbox_data = cls(mailbox_path / mailbox_id)

            # Copy tokens to new location
            try:
                import shutil

                shutil.copy2(token_file, new_mailbox_data.tokens_file)
                logger.info(
                    f"Migrated {mailbox_id} tokens to {new_mailbox_data.tokens_file}"
                )
                mailboxes[mailbox_id] = new_mailbox_data

            except Exception as e:
                logger.error(f"Failed to migrate {mailbox_id}: {e}")

        logger.info(
            f"Migrated {len(mailboxes)} mailboxes from {tokens_dir} to {mailbox_dir}"
        )
        return mailboxes
