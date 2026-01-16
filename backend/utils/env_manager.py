"""Environment file manager for secure .env file editing."""
import os
import re
from pathlib import Path
from typing import Optional
from datetime import datetime
import shutil

import structlog

logger = structlog.get_logger()

# Only these environment variables can be modified via the API
# This is a security measure to prevent arbitrary env var injection
ALLOWED_ENV_VARS = {
    # AI Provider API Keys
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "MISTRAL_API_KEY",
    "XAI_API_KEY",
    # Market Data API Keys
    "ALPHA_VANTAGE_API_KEY",
    "NEWS_API_KEY",
    "FRED_API_KEY",
}

# Map settings keys to environment variable names
SETTING_TO_ENV_MAP = {
    "google_api_key": "GOOGLE_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "mistral_api_key": "MISTRAL_API_KEY",
    "xai_api_key": "XAI_API_KEY",
    "alpha_vantage_api_key": "ALPHA_VANTAGE_API_KEY",
    "news_api_key": "NEWS_API_KEY",
    "fred_api_key": "FRED_API_KEY",
}


class EnvFileManager:
    """
    Manages reading and writing to .env files.

    Security features:
    - Only allows modification of whitelisted environment variables
    - Creates backups before modifying
    - Validates variable names and values
    """

    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize the env file manager.

        Args:
            env_path: Path to .env file. Defaults to project root .env
        """
        if env_path:
            self.env_path = Path(env_path)
        else:
            # Find project root (where .env should be)
            # Go up from backend/utils/ to project root
            self.env_path = Path(__file__).parent.parent.parent / ".env"

        self.env_example_path = self.env_path.parent / ".env.example"

    def _ensure_env_exists(self) -> bool:
        """Ensure .env file exists, create from .env.example if needed."""
        if self.env_path.exists():
            return True

        if self.env_example_path.exists():
            logger.info("Creating .env from .env.example")
            shutil.copy(self.env_example_path, self.env_path)
            return True

        # Create minimal .env file
        logger.info("Creating new .env file")
        self.env_path.write_text("# Equities AI Environment Configuration\n# Created automatically\n\n")
        return True

    def _create_backup(self) -> Optional[Path]:
        """Create a backup of the current .env file."""
        if not self.env_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.env_path.parent / f".env.backup.{timestamp}"
        shutil.copy(self.env_path, backup_path)
        logger.info("Created .env backup", backup_path=str(backup_path))
        return backup_path

    def _validate_var_name(self, name: str) -> bool:
        """Validate environment variable name is allowed."""
        return name in ALLOWED_ENV_VARS

    def _validate_value(self, value: str) -> bool:
        """Validate environment variable value is safe."""
        # Prevent shell injection
        dangerous_chars = ['`', '$', '(', ')', ';', '|', '&', '\n', '\r']
        return not any(char in value for char in dangerous_chars)

    def _parse_env_file(self) -> dict[str, tuple[str, str]]:
        """
        Parse .env file into dict.

        Returns:
            Dict mapping var name to (value, original_line)
        """
        if not self.env_path.exists():
            return {}

        content = self.env_path.read_text()
        result = {}

        for line in content.split('\n'):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # Parse KEY=value
            match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', stripped)
            if match:
                key = match.group(1)
                value = match.group(2).strip('"\'')  # Remove quotes if present
                result[key] = (value, line)

        return result

    def get(self, var_name: str) -> Optional[str]:
        """
        Get an environment variable value.

        First checks os.environ (runtime), then .env file.

        Args:
            var_name: Environment variable name

        Returns:
            Value or None if not set
        """
        # Check runtime environment first
        if var_name in os.environ and os.environ[var_name]:
            return os.environ[var_name]

        # Check .env file
        env_vars = self._parse_env_file()
        if var_name in env_vars:
            value, _ = env_vars[var_name]
            return value if value else None

        return None

    def set(self, var_name: str, value: str, reload_env: bool = True) -> bool:
        """
        Set an environment variable in the .env file.

        Args:
            var_name: Environment variable name (must be in ALLOWED_ENV_VARS)
            value: Value to set
            reload_env: Whether to also update os.environ

        Returns:
            True if successful

        Raises:
            ValueError: If var_name is not allowed or value is invalid
            PermissionError: If .env file cannot be written
        """
        # Validate
        if not self._validate_var_name(var_name):
            raise ValueError(f"Environment variable '{var_name}' is not allowed to be modified via API")

        if not self._validate_value(value):
            raise ValueError(f"Invalid value for environment variable (contains dangerous characters)")

        # Ensure .env exists
        self._ensure_env_exists()

        # Create backup
        self._create_backup()

        # Read current content
        content = self.env_path.read_text()
        lines = content.split('\n')

        # Check if variable already exists
        var_pattern = re.compile(f'^{re.escape(var_name)}=')
        found = False
        new_lines = []

        for line in lines:
            if var_pattern.match(line.strip()):
                # Replace existing line
                new_lines.append(f'{var_name}={value}')
                found = True
            else:
                new_lines.append(line)

        if not found:
            # Add new variable
            # Find the right section or add at end
            new_lines.append(f'{var_name}={value}')

        # Write back
        self.env_path.write_text('\n'.join(new_lines))

        logger.info("Updated .env file", var_name=var_name, has_value=bool(value))

        # Optionally reload into runtime environment
        if reload_env:
            os.environ[var_name] = value

        return True

    def delete(self, var_name: str, reload_env: bool = True) -> bool:
        """
        Remove an environment variable from the .env file.

        Args:
            var_name: Environment variable name
            reload_env: Whether to also update os.environ

        Returns:
            True if successful
        """
        if not self._validate_var_name(var_name):
            raise ValueError(f"Environment variable '{var_name}' is not allowed to be modified via API")

        if not self.env_path.exists():
            return False

        # Create backup
        self._create_backup()

        # Read and filter
        content = self.env_path.read_text()
        lines = content.split('\n')
        var_pattern = re.compile(f'^{re.escape(var_name)}=')

        new_lines = [line for line in lines if not var_pattern.match(line.strip())]

        # Write back
        self.env_path.write_text('\n'.join(new_lines))

        logger.info("Removed from .env file", var_name=var_name)

        # Optionally remove from runtime environment
        if reload_env and var_name in os.environ:
            del os.environ[var_name]

        return True

    def get_all_api_keys_status(self) -> dict[str, dict]:
        """
        Get status of all API keys.

        Returns:
            Dict mapping setting key to status info
        """
        result = {}

        for setting_key, env_var in SETTING_TO_ENV_MAP.items():
            value = self.get(env_var)
            provider = setting_key.replace("_api_key", "")

            result[provider] = {
                "configured": bool(value),
                "env_var": env_var,
                "source": "env" if value else None,
                # Never return actual key values
            }

        return result

    def setting_key_to_env_var(self, setting_key: str) -> Optional[str]:
        """Convert a setting key to its environment variable name."""
        return SETTING_TO_ENV_MAP.get(setting_key)


# Global instance
_env_manager: Optional[EnvFileManager] = None


def get_env_manager() -> EnvFileManager:
    """Get or create the global env manager instance."""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvFileManager()
    return _env_manager
