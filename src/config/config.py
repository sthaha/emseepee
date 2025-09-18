# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""Configuration management for Gmail MCP Server."""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Gmail:
    """Gmail MCP Server configuration data class."""

    # Required settings
    creds_file: str
    mailbox_dir: str

    # MCP settings
    mode: str = "http"

    # HTTP settings
    port: int = 63417
    addr: str = "localhost"

    # Optional settings
    mailbox: Optional[str] = None
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate mode
        if self.mode not in ("http", "stdio"):
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'http' or 'stdio'")

        # Validate port
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError(
                f"Invalid port: {self.port}. Must be integer between 1-65535"
            )

        # Validate log level
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR")
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log_level: {self.log_level}. Must be one of {valid_levels}"
            )

        # Normalize log level to uppercase
        self.log_level = self.log_level.upper()


class Loader:
    """Handles loading and merging of configuration from files and CLI arguments."""

    @staticmethod
    def load_config_file(config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            config_file: Path to YAML configuration file

        Returns:
            Dictionary with configuration values

        Raises:
            ValueError: If config file doesn't exist or is invalid
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise ValueError(f"Configuration file does not exist: {config_file}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file {config_file}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to read configuration file {config_file}: {e}")

        # Process paths and nested configuration
        return Loader._process_config(config, config_path)

    @staticmethod
    def _process_config(config: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
        """Process configuration by expanding paths and flattening nested structure."""
        processed = config.copy()

        # Convert relative paths to absolute paths
        for path_key in ["creds_file", "mailbox_dir"]:
            if path_key in processed and processed[path_key]:
                file_path = Path(processed[path_key]).expanduser()
                if not file_path.is_absolute():
                    # Make relative to config file directory
                    processed[path_key] = str(config_path.parent / file_path)
                else:
                    processed[path_key] = str(file_path)

        # Handle nested configuration
        # Extract values from nested mcp.* and http.* settings
        if "mcp" in processed and isinstance(processed["mcp"], dict):
            if "mode" in processed["mcp"]:
                processed["mode"] = processed["mcp"]["mode"]

        if "http" in processed and isinstance(processed["http"], dict):
            if "port" in processed["http"]:
                processed["port"] = processed["http"]["port"]
            if "addr" in processed["http"]:
                processed["addr"] = processed["http"]["addr"]

        return processed

    @staticmethod
    def merge_with_cli_args(config: Dict[str, Any], **cli_args) -> Dict[str, Any]:
        """Merge configuration file with CLI arguments, with CLI taking precedence.

        Args:
            config: Configuration dictionary from file
            **cli_args: CLI arguments as keyword arguments

        Returns:
            Merged configuration with CLI args overriding config file values
        """
        merged = config.copy()

        # CLI args override config file values (skip None values)
        for key, value in cli_args.items():
            if value is not None:
                merged[key] = value

        return merged

    @staticmethod
    def create(**kwargs) -> Gmail:
        """Create a Gmail config instance from keyword arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            Gmail instance

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Extract required parameters
        creds_file = kwargs.get("creds_file")
        mailbox_dir = kwargs.get("mailbox_dir")

        if not creds_file:
            raise ValueError("Missing required parameter: creds_file")
        if not mailbox_dir:
            raise ValueError("Missing required parameter: mailbox_dir")

        # Create config with defaults for optional parameters
        return Gmail(
            creds_file=creds_file,
            mailbox_dir=mailbox_dir,
            mode=kwargs.get("mode", "http"),
            port=kwargs.get("port", 63417),
            addr=kwargs.get("addr", "localhost"),
            mailbox=kwargs.get("mailbox"),
            log_level=kwargs.get("log_level", "INFO"),
        )

    @classmethod
    def from_file_and_cli(cls, config_file: Optional[str] = None, **cli_args) -> Gmail:
        """Load configuration from file and CLI arguments.

        Args:
            config_file: Optional path to YAML configuration file
            **cli_args: CLI arguments to override config file values

        Returns:
            Gmail instance

        Raises:
            ValueError: If configuration is invalid or required parameters missing
        """
        # Start with empty config
        config = {}

        # Load from file if provided
        if config_file:
            config = cls.load_config_file(config_file)

        # Merge with CLI arguments
        merged_config = cls.merge_with_cli_args(config, **cli_args)

        # Create and return validated config instance
        return cls.create(**merged_config)
