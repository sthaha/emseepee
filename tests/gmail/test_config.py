# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""Tests for the config module.

This module provides comprehensive test coverage for:
- Gmail configuration data class validation
- Configuration file loading (nested and legacy formats)
- Path resolution (relative, absolute, home directory expansion)
- CLI argument merging and overrides
- Error handling for invalid configurations
- Edge cases (empty files, null values, malformed YAML)
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from config import Loader, Gmail


class TestGmailConfig:
    """Test the Gmail configuration data class."""

    def test_valid_config_creation(self):
        """Test creating a valid Gmail config."""
        config = Gmail(
            creds_file="/path/to/creds.json", mailbox_dir="/path/to/mailboxes"
        )

        assert config.creds_file == "/path/to/creds.json"
        assert config.mailbox_dir == "/path/to/mailboxes"
        assert config.mode == "http"  # default
        assert config.port == 63417  # default
        assert config.addr == "localhost"  # default
        assert config.mailbox is None  # default
        assert config.log_level == "INFO"  # default

    def test_config_with_custom_values(self):
        """Test creating Gmail config with custom values."""
        config = Gmail(
            creds_file="/custom/creds.json",
            mailbox_dir="/custom/mailboxes",
            mode="stdio",
            port=8080,
            addr="0.0.0.0",
            mailbox="work",
            log_level="DEBUG",
        )

        assert config.creds_file == "/custom/creds.json"
        assert config.mailbox_dir == "/custom/mailboxes"
        assert config.mode == "stdio"
        assert config.port == 8080
        assert config.addr == "0.0.0.0"
        assert config.mailbox == "work"
        assert config.log_level == "DEBUG"

    def test_invalid_mode_validation(self):
        """Test validation of invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode: invalid"):
            Gmail(
                creds_file="/path/to/creds.json",
                mailbox_dir="/path/to/mailboxes",
                mode="invalid",
            )

    def test_invalid_port_validation(self):
        """Test validation of invalid port."""
        with pytest.raises(ValueError, match="Invalid port: 0"):
            Gmail(
                creds_file="/path/to/creds.json",
                mailbox_dir="/path/to/mailboxes",
                port=0,
            )

        with pytest.raises(ValueError, match="Invalid port: 70000"):
            Gmail(
                creds_file="/path/to/creds.json",
                mailbox_dir="/path/to/mailboxes",
                port=70000,
            )

    def test_invalid_log_level_validation(self):
        """Test validation of invalid log level."""
        with pytest.raises(ValueError, match="Invalid log_level: INVALID"):
            Gmail(
                creds_file="/path/to/creds.json",
                mailbox_dir="/path/to/mailboxes",
                log_level="INVALID",
            )

    def test_log_level_normalization(self):
        """Test that log level is normalized to uppercase."""
        config = Gmail(
            creds_file="/path/to/creds.json",
            mailbox_dir="/path/to/mailboxes",
            log_level="debug",
        )
        assert config.log_level == "DEBUG"


class TestConfigLoader:
    """Test the configuration loader class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "/test/creds.json",
                "mailbox_dir": "/test/mailboxes",
                "mcp": {"mode": "stdio"},
                "http": {"port": 8080, "addr": "0.0.0.0"},
                "mailbox": "personal",
            }
            yaml.dump(config_data, f)
            yield Path(f.name)
        Path(f.name).unlink()  # cleanup

    @pytest.fixture
    def temp_legacy_config_file(self):
        """Create a temporary legacy format config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "/legacy/creds.json",
                "mailbox_dir": "/legacy/mailboxes",
                "mode": "http",
                "port": 9999,
                "addr": "127.0.0.1",
            }
            yaml.dump(config_data, f)
            yield Path(f.name)
        Path(f.name).unlink()  # cleanup

    @pytest.fixture
    def temp_relative_config_file(self):
        """Create a temporary config file with relative paths."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "./creds.json",
                "mailbox_dir": "./mailboxes",
                "mcp": {"mode": "http"},
            }
            yaml.dump(config_data, f)
            yield Path(f.name)
        Path(f.name).unlink()  # cleanup

    @pytest.fixture
    def temp_home_config_file(self):
        """Create a temporary config file with home directory paths."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "~/.creds/gmail/creds.json",
                "mailbox_dir": "~/.creds/gmail/mailboxes",
            }
            yaml.dump(config_data, f)
            yield Path(f.name)
        Path(f.name).unlink()  # cleanup

    def test_load_config_file_nested_format(self, temp_config_file):
        """Test loading config file with nested format."""
        config = Loader.load_config_file(str(temp_config_file))

        assert config["creds_file"] == "/test/creds.json"
        assert config["mailbox_dir"] == "/test/mailboxes"
        assert config["mode"] == "stdio"  # from mcp.mode
        assert config["port"] == 8080  # from http.port
        assert config["addr"] == "0.0.0.0"  # from http.addr
        assert config["mailbox"] == "personal"

    def test_load_config_file_legacy_format(self, temp_legacy_config_file):
        """Test loading config file with legacy format."""
        config = Loader.load_config_file(str(temp_legacy_config_file))

        assert config["creds_file"] == "/legacy/creds.json"
        assert config["mailbox_dir"] == "/legacy/mailboxes"
        assert config["mode"] == "http"
        assert config["port"] == 9999
        assert config["addr"] == "127.0.0.1"

    def test_load_config_file_relative_paths(self, temp_relative_config_file):
        """Test loading config file with relative paths."""
        config = Loader.load_config_file(str(temp_relative_config_file))
        config_dir = Path(temp_relative_config_file).parent

        assert config["creds_file"] == str(config_dir / "creds.json")
        assert config["mailbox_dir"] == str(config_dir / "mailboxes")

    def test_load_config_file_home_expansion(self, temp_home_config_file):
        """Test loading config file with home directory expansion."""
        config = Loader.load_config_file(str(temp_home_config_file))
        home_dir = Path.home()

        assert config["creds_file"] == str(home_dir / ".creds/gmail/creds.json")
        assert config["mailbox_dir"] == str(home_dir / ".creds/gmail/mailboxes")

    def test_load_nonexistent_config_file(self):
        """Test loading nonexistent config file raises error."""
        with pytest.raises(ValueError, match="Configuration file does not exist"):
            Loader.load_config_file("/nonexistent/config.yaml")

    def test_load_invalid_yaml_file(self):
        """Test loading invalid YAML file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(ValueError, match="Invalid YAML"):
                Loader.load_config_file(f.name)

            Path(f.name).unlink()

    def test_merge_with_cli_args(self):
        """Test merging config with CLI arguments."""
        config = {
            "creds_file": "/config/creds.json",
            "mailbox_dir": "/config/mailboxes",
            "mode": "stdio",
            "port": 8080,
        }

        merged = Loader.merge_with_cli_args(
            config,
            creds_file="/cli/creds.json",  # override
            mode="http",  # override
            mailbox="personal",  # new
            addr=None,  # should be ignored
        )

        assert merged["creds_file"] == "/cli/creds.json"  # overridden
        assert merged["mailbox_dir"] == "/config/mailboxes"  # preserved
        assert merged["mode"] == "http"  # overridden
        assert merged["port"] == 8080  # preserved
        assert merged["mailbox"] == "personal"  # added
        assert "addr" not in merged  # None values ignored

    def test_create_valid_config(self):
        """Test creating valid config from kwargs."""
        config = Loader.create(
            creds_file="/test/creds.json",
            mailbox_dir="/test/mailboxes",
            mode="stdio",
            port=8080,
        )

        assert isinstance(config, Gmail)
        assert config.creds_file == "/test/creds.json"
        assert config.mailbox_dir == "/test/mailboxes"
        assert config.mode == "stdio"
        assert config.port == 8080

    def test_create_missing_required_params(self):
        """Test creating config with missing required parameters."""
        with pytest.raises(ValueError, match="Missing required parameter: creds_file"):
            Loader.create(mailbox_dir="/test/mailboxes")

        with pytest.raises(ValueError, match="Missing required parameter: mailbox_dir"):
            Loader.create(creds_file="/test/creds.json")

    def test_from_file_and_cli(self, temp_config_file):
        """Test loading from file and CLI combined."""
        config = Loader.from_file_and_cli(
            config_file=str(temp_config_file),
            port=7777,  # override config file
            mailbox="work",  # override config file
        )

        assert isinstance(config, Gmail)
        assert config.creds_file == "/test/creds.json"  # from file
        assert config.mailbox_dir == "/test/mailboxes"  # from file
        assert config.mode == "stdio"  # from file (nested)
        assert config.port == 7777  # from CLI override
        assert config.addr == "0.0.0.0"  # from file (nested)
        assert config.mailbox == "work"  # from CLI override

    def test_from_file_and_cli_no_file(self):
        """Test loading from CLI only (no config file)."""
        config = Loader.from_file_and_cli(
            creds_file="/cli/creds.json",
            mailbox_dir="/cli/mailboxes",
            mode="stdio",
            port=9999,
        )

        assert isinstance(config, Gmail)
        assert config.creds_file == "/cli/creds.json"
        assert config.mailbox_dir == "/cli/mailboxes"
        assert config.mode == "stdio"
        assert config.port == 9999

    def test_from_file_and_cli_missing_required(self, temp_config_file):
        """Test error when required params missing after merge."""
        # Create config file without required fields
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"mode": "http"}, f)

            with pytest.raises(ValueError, match="Missing required parameter"):
                Loader.from_file_and_cli(config_file=f.name)

            Path(f.name).unlink()

    def test_nested_precedence_over_legacy(self):
        """Test that nested config takes precedence over legacy format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "/test/creds.json",
                "mailbox_dir": "/test/mailboxes",
                # Legacy format
                "mode": "stdio",
                "port": 8888,
                "addr": "127.0.0.1",
                # Nested format (should take precedence)
                "mcp": {"mode": "http"},
                "http": {"port": 9999, "addr": "0.0.0.0"},
            }
            yaml.dump(config_data, f)
            f.flush()

            config = Loader.load_config_file(f.name)

            assert config["mode"] == "http"  # nested takes precedence
            assert config["port"] == 9999  # nested takes precedence
            assert config["addr"] == "0.0.0.0"  # nested takes precedence

            Path(f.name).unlink()

    def test_empty_config_file(self):
        """Test loading empty config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # empty file
            f.flush()

            config = Loader.load_config_file(f.name)
            assert config == {}

            Path(f.name).unlink()

    def test_config_file_with_null_values(self):
        """Test loading config file with null values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "creds_file": "/test/creds.json",
                "mailbox_dir": "/test/mailboxes",
                "mailbox": None,
                "log_level": None,
            }
            yaml.dump(config_data, f)
            f.flush()

            config = Loader.load_config_file(f.name)

            assert config["creds_file"] == "/test/creds.json"
            assert config["mailbox_dir"] == "/test/mailboxes"
            assert "mailbox" in config  # null values preserved
            assert config["mailbox"] is None

            Path(f.name).unlink()
