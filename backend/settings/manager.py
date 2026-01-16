"""Settings management with database persistence and environment variable support."""
import json
import os
from typing import Any, Optional
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import structlog

from backend.database.models import Setting, SettingHistory
from backend.settings.defaults import DEFAULT_SETTINGS
from backend.settings.validator import SettingsValidator

logger = structlog.get_logger()

# Mapping of setting keys to environment variable names
# API keys should ALWAYS be loaded from environment variables for security
ENV_VAR_MAPPING = {
    ("api_config", "google_api_key"): "GOOGLE_API_KEY",
    ("api_config", "openai_api_key"): "OPENAI_API_KEY",
    ("api_config", "anthropic_api_key"): "ANTHROPIC_API_KEY",
    ("api_config", "mistral_api_key"): "MISTRAL_API_KEY",
    ("api_config", "xai_api_key"): "XAI_API_KEY",
    ("api_config", "alpha_vantage_api_key"): "ALPHA_VANTAGE_API_KEY",
    ("api_config", "news_api_key"): "NEWS_API_KEY",
    ("api_config", "fred_api_key"): "FRED_API_KEY",
}


class SettingsManager:
    """
    Manager for database-backed settings with caching.

    Provides CRUD operations, validation, and hot-reload support.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_loaded = False

    async def get(
        self,
        key: str,
        category: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """
        Get a setting value by key.

        For API keys, environment variables take priority over database values.
        This ensures secrets are loaded from .env files, not stored in the database.

        Args:
            key: The setting key
            category: Optional category to narrow search
            default: Default value if not found

        Returns:
            The setting value (type-coerced) or default
        """
        # Check environment variable first for sensitive API keys
        if category:
            env_var = ENV_VAR_MAPPING.get((category, key))
            if env_var:
                env_value = os.environ.get(env_var)
                if env_value:
                    return env_value

        if category:
            result = await self.db.execute(
                select(Setting).where(
                    and_(Setting.category == category, Setting.key == key)
                )
            )
        else:
            result = await self.db.execute(
                select(Setting).where(Setting.key == key)
            )

        setting = result.scalar_one_or_none()

        if setting is None:
            # Try to get from defaults
            if category and category in DEFAULT_SETTINGS:
                if key in DEFAULT_SETTINGS[category]:
                    return self._coerce_default(DEFAULT_SETTINGS[category][key])
            return default

        return setting.get_typed_value()

    def _coerce_default(self, default_config: dict) -> Any:
        """Coerce default value to its proper type."""
        value = default_config.get("value")
        value_type = default_config.get("value_type", "string")

        if value is None or value == "":
            return None

        if value_type == "integer":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        return value

    async def get_api_key_status(self) -> dict[str, dict[str, Any]]:
        """
        Get the configuration status of all API keys.

        Returns status of each provider's API key:
        - configured: bool - whether the key is set
        - source: "env" | "database" | None - where the key comes from

        This method NEVER returns actual key values for security.
        """
        status = {}

        for (category, key), env_var in ENV_VAR_MAPPING.items():
            provider = key.replace("_api_key", "")

            # Check environment variable first
            env_value = os.environ.get(env_var)
            if env_value and env_value.strip():
                status[provider] = {
                    "configured": True,
                    "source": "env",
                    "env_var": env_var,
                }
            else:
                # Check database
                result = await self.db.execute(
                    select(Setting).where(
                        and_(Setting.category == category, Setting.key == key)
                    )
                )
                setting = result.scalar_one_or_none()

                if setting and setting.value and setting.value.strip():
                    status[provider] = {
                        "configured": True,
                        "source": "database",
                        "env_var": env_var,
                    }
                else:
                    status[provider] = {
                        "configured": False,
                        "source": None,
                        "env_var": env_var,
                    }

        return status

    async def get_all(self, category: Optional[str] = None) -> dict[str, Any]:
        """
        Get all settings, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            Dict of category -> key -> value
        """
        if category:
            result = await self.db.execute(
                select(Setting).where(Setting.category == category)
            )
        else:
            result = await self.db.execute(select(Setting))

        settings = result.scalars().all()
        output: dict[str, dict[str, Any]] = {}

        for setting in settings:
            if setting.category not in output:
                output[setting.category] = {}
            output[setting.category][setting.key] = {
                "value": setting.get_typed_value(),
                "value_type": setting.value_type,
                "description": setting.description,
                "is_sensitive": setting.is_sensitive,
                "updated_at": setting.updated_at.isoformat() if setting.updated_at else None,
            }

        return output

    async def set(
        self,
        category: str,
        key: str,
        value: Any,
        value_type: str = "string",
        description: Optional[str] = None,
        is_sensitive: bool = False,
        validation_rules: Optional[dict] = None,
        updated_by: Optional[str] = None,
    ) -> Setting:
        """
        Set or update a setting value.

        Args:
            category: Setting category
            key: Setting key
            value: New value
            value_type: Type of value (string, integer, float, boolean, json)
            description: Optional description
            is_sensitive: Whether value should be masked
            validation_rules: Optional validation rules
            updated_by: User who made the change

        Returns:
            The updated Setting object

        Raises:
            ValueError: If validation fails
        """
        # Validate the value
        str_value = str(value) if value is not None else ""
        validation_result = SettingsValidator.validate(
            str_value, value_type, validation_rules
        )

        if not validation_result.valid:
            raise ValueError(f"Validation failed: {validation_result.error}")

        # Check if setting exists
        result = await self.db.execute(
            select(Setting).where(
                and_(Setting.category == category, Setting.key == key)
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing setting
            old_value = existing.value
            existing.value = str_value
            existing.value_type = value_type
            if description:
                existing.description = description
            existing.is_sensitive = is_sensitive
            if validation_rules:
                existing.validation_rules = validation_rules
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()

            # Record history
            history = SettingHistory(
                setting_id=existing.id,
                category=category,
                key=key,
                old_value=old_value,
                new_value=str_value,
                changed_by=updated_by,
                change_type="update",
            )
            self.db.add(history)

            await self.db.commit()
            await self.db.refresh(existing)

            logger.info(
                "Setting updated",
                category=category,
                key=key,
                updated_by=updated_by,
            )
            return existing

        else:
            # Create new setting
            setting = Setting(
                category=category,
                key=key,
                value=str_value,
                value_type=value_type,
                description=description,
                is_sensitive=is_sensitive,
                validation_rules=validation_rules,
                updated_by=updated_by,
            )
            self.db.add(setting)
            await self.db.commit()
            await self.db.refresh(setting)

            # Record history
            history = SettingHistory(
                setting_id=setting.id,
                category=category,
                key=key,
                old_value=None,
                new_value=str_value,
                changed_by=updated_by,
                change_type="create",
            )
            self.db.add(history)
            await self.db.commit()

            logger.info(
                "Setting created",
                category=category,
                key=key,
                updated_by=updated_by,
            )
            return setting

    async def delete(
        self,
        category: str,
        key: str,
        deleted_by: Optional[str] = None,
    ) -> bool:
        """
        Delete a setting.

        Args:
            category: Setting category
            key: Setting key
            deleted_by: User who deleted the setting

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(Setting).where(
                and_(Setting.category == category, Setting.key == key)
            )
        )
        setting = result.scalar_one_or_none()

        if not setting:
            return False

        # Record deletion in history
        history = SettingHistory(
            setting_id=setting.id,
            category=category,
            key=key,
            old_value=setting.value,
            new_value=None,
            changed_by=deleted_by,
            change_type="delete",
        )
        self.db.add(history)

        await self.db.delete(setting)
        await self.db.commit()

        logger.info(
            "Setting deleted",
            category=category,
            key=key,
            deleted_by=deleted_by,
        )
        return True

    async def get_history(
        self,
        category: Optional[str] = None,
        key: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get settings change history.

        Args:
            category: Optional category filter
            key: Optional key filter
            limit: Maximum records to return

        Returns:
            List of history records
        """
        query = select(SettingHistory).order_by(SettingHistory.changed_at.desc())

        if category:
            query = query.where(SettingHistory.category == category)
        if key:
            query = query.where(SettingHistory.key == key)

        query = query.limit(limit)
        result = await self.db.execute(query)
        records = result.scalars().all()

        return [
            {
                "id": r.id,
                "category": r.category,
                "key": r.key,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                "changed_by": r.changed_by,
                "change_type": r.change_type,
            }
            for r in records
        ]

    async def reset_to_defaults(
        self,
        category: Optional[str] = None,
        reset_by: Optional[str] = None,
    ) -> int:
        """
        Reset settings to default values.

        Args:
            category: Optional category to reset (None = all)
            reset_by: User who initiated the reset

        Returns:
            Number of settings reset
        """
        count = 0
        categories = [category] if category else DEFAULT_SETTINGS.keys()

        for cat in categories:
            if cat not in DEFAULT_SETTINGS:
                continue

            for key, config in DEFAULT_SETTINGS[cat].items():
                await self.set(
                    category=cat,
                    key=key,
                    value=config["value"],
                    value_type=config["value_type"],
                    description=config.get("description"),
                    is_sensitive=config.get("is_sensitive", False),
                    validation_rules=config.get("validation_rules"),
                    updated_by=reset_by,
                )
                count += 1

        logger.info(
            "Settings reset to defaults",
            category=category,
            count=count,
            reset_by=reset_by,
        )
        return count

    async def export_settings(self, include_sensitive: bool = False) -> dict:
        """
        Export all settings as JSON-serializable dict.

        Args:
            include_sensitive: Whether to include sensitive values

        Returns:
            Dict of all settings
        """
        all_settings = await self.get_all()

        if not include_sensitive:
            for category in all_settings.values():
                for key, config in category.items():
                    if config.get("is_sensitive"):
                        config["value"] = "***REDACTED***"

        return all_settings

    async def import_settings(
        self,
        settings: dict,
        imported_by: Optional[str] = None,
        skip_sensitive: bool = True,
    ) -> int:
        """
        Import settings from a dict.

        Args:
            settings: Dict of category -> key -> config
            imported_by: User who initiated the import
            skip_sensitive: Whether to skip sensitive settings

        Returns:
            Number of settings imported
        """
        count = 0

        for category, keys in settings.items():
            for key, config in keys.items():
                if skip_sensitive and config.get("is_sensitive"):
                    continue

                await self.set(
                    category=category,
                    key=key,
                    value=config.get("value"),
                    value_type=config.get("value_type", "string"),
                    description=config.get("description"),
                    is_sensitive=config.get("is_sensitive", False),
                    validation_rules=config.get("validation_rules"),
                    updated_by=imported_by,
                )
                count += 1

        logger.info(
            "Settings imported",
            count=count,
            imported_by=imported_by,
        )
        return count


# Synchronous version for non-async contexts
class SyncSettingsManager:
    """Synchronous settings manager for use outside async context."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(
        self,
        key: str,
        category: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """Get a setting value by key."""
        if category:
            setting = self.db.query(Setting).filter(
                and_(Setting.category == category, Setting.key == key)
            ).first()
        else:
            setting = self.db.query(Setting).filter(Setting.key == key).first()

        if setting is None:
            if category and category in DEFAULT_SETTINGS:
                if key in DEFAULT_SETTINGS[category]:
                    return self._coerce_default(DEFAULT_SETTINGS[category][key])
            return default

        return setting.get_typed_value()

    def _coerce_default(self, default_config: dict) -> Any:
        """Coerce default value to its proper type."""
        value = default_config.get("value")
        value_type = default_config.get("value_type", "string")

        if value is None or value == "":
            return None

        if value_type == "integer":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        return value
