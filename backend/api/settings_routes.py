"""Settings API endpoints."""
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, User
from backend.settings import SettingsManager, SettingsValidator
from backend.api.websocket import broadcast_settings_change
from backend.api.auth_routes import get_current_active_user, require_admin
from backend.utils.env_manager import get_env_manager, SETTING_TO_ENV_MAP

router = APIRouter()


class SettingCreate(BaseModel):
    """Request model for creating a setting."""
    category: str
    key: str
    value: Any
    value_type: str = "string"
    description: Optional[str] = None
    is_sensitive: bool = False
    validation_rules: Optional[dict] = None


class SettingUpdate(BaseModel):
    """Request model for updating a setting."""
    value: Any
    value_type: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None
    validation_rules: Optional[dict] = None


class SettingsImport(BaseModel):
    """Request model for importing settings."""
    settings: dict
    skip_sensitive: bool = True


class ApiKeyUpdate(BaseModel):
    """Request model for updating an API key in .env file."""
    provider: str
    api_key: str


@router.get("")
async def get_all_settings(
    category: Optional[str] = Query(None, description="Filter by category"),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all settings, optionally filtered by category."""
    manager = SettingsManager(db)
    settings = await manager.get_all(category)
    return {"settings": settings}


@router.get("/categories")
async def get_categories(
    user: User = Depends(get_current_active_user),
) -> dict:
    """Get list of valid setting categories."""
    return {
        "categories": [
            {"id": "api_config", "name": "API Configuration", "description": "API keys and connection settings"},
            {"id": "agent_config", "name": "Agent Configuration", "description": "Enable/disable and configure agents"},
            {"id": "risk_management", "name": "Risk Management", "description": "Portfolio risk parameters"},
            {"id": "scheduling", "name": "Scheduling", "description": "Agent run schedules"},
            {"id": "performance", "name": "Performance & Cost", "description": "Token budgets and alerts"},
            {"id": "ui_preferences", "name": "UI Preferences", "description": "Dashboard appearance settings"},
            {"id": "system", "name": "System Configuration", "description": "Logging and system settings"},
        ]
    }


@router.get("/api-keys/status")
async def get_api_key_status(
    user: User = Depends(get_current_active_user),
) -> dict:
    """
    Get the configuration status of all API keys.

    Returns which providers have API keys configured and whether they
    come from environment variables or the database.

    IMPORTANT: This endpoint NEVER returns actual API key values.
    """
    env_manager = get_env_manager()
    status = env_manager.get_all_api_keys_status()
    return {
        "api_keys": status,
        "note": "API keys are stored in the .env file for security"
    }


@router.put("/api-keys/{provider}")
async def update_api_key(
    provider: str,
    data: ApiKeyUpdate,
    admin: User = Depends(require_admin),
) -> dict:
    """
    Update an API key in the .env file.

    This endpoint writes directly to the .env file, which is the secure
    way to store API keys. The key will be immediately available to the
    application without restart.

    Args:
        provider: Provider name (google, openai, anthropic, mistral, xai, etc.)
        data: ApiKeyUpdate with the new API key

    Returns:
        Status of the update
    """
    # Map provider to setting key
    setting_key = f"{provider}_api_key"
    env_manager = get_env_manager()

    # Get the environment variable name
    env_var = env_manager.setting_key_to_env_var(setting_key)
    if not env_var:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}. Valid providers: google, openai, anthropic, mistral, xai, alpha_vantage, news, fred"
        )

    try:
        env_manager.set(env_var, data.api_key)
        return {
            "status": "updated",
            "provider": provider,
            "env_var": env_var,
            "message": f"API key for {provider} saved to .env file"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cannot write to .env file: {str(e)}"
        )


@router.delete("/api-keys/{provider}")
async def delete_api_key(
    provider: str,
    admin: User = Depends(require_admin),
) -> dict:
    """
    Remove an API key from the .env file.

    Args:
        provider: Provider name

    Returns:
        Status of the deletion
    """
    setting_key = f"{provider}_api_key"
    env_manager = get_env_manager()

    env_var = env_manager.setting_key_to_env_var(setting_key)
    if not env_var:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}"
        )

    try:
        env_manager.delete(env_var)
        return {
            "status": "deleted",
            "provider": provider,
            "env_var": env_var,
            "message": f"API key for {provider} removed from .env file"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{category}")
async def get_category_settings(
    category: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all settings in a category."""
    if not SettingsValidator.validate_category(category):
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    manager = SettingsManager(db)
    settings = await manager.get_all(category)
    return {"category": category, "settings": settings.get(category, {})}


@router.get("/{category}/{key}")
async def get_setting(
    category: str,
    key: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a specific setting."""
    if not SettingsValidator.validate_category(category):
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    manager = SettingsManager(db)
    value = await manager.get(key, category)

    if value is None:
        raise HTTPException(
            status_code=404,
            detail=f"Setting not found: {category}/{key}"
        )

    # Get full setting details
    all_settings = await manager.get_all(category)
    setting_details = all_settings.get(category, {}).get(key, {})

    return {
        "category": category,
        "key": key,
        "value": value if not setting_details.get("is_sensitive") else "***REDACTED***",
        "value_type": setting_details.get("value_type", "string"),
        "description": setting_details.get("description"),
        "is_sensitive": setting_details.get("is_sensitive", False),
    }


@router.post("")
async def create_setting(
    setting: SettingCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new setting."""
    if not SettingsValidator.validate_category(setting.category):
        raise HTTPException(status_code=400, detail=f"Invalid category: {setting.category}")

    if not SettingsValidator.validate_value_type(setting.value_type):
        raise HTTPException(status_code=400, detail=f"Invalid value_type: {setting.value_type}")

    manager = SettingsManager(db)

    try:
        result = await manager.set(
            category=setting.category,
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            description=setting.description,
            is_sensitive=setting.is_sensitive,
            validation_rules=setting.validation_rules,
            updated_by="api",
        )

        # Broadcast change via WebSocket
        await broadcast_settings_change(setting.category, setting.key, str(setting.value))

        return {
            "status": "created",
            "category": result.category,
            "key": result.key,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{category}/{key}")
async def update_setting(
    category: str,
    key: str,
    update: SettingUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update an existing setting."""
    if not SettingsValidator.validate_category(category):
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    manager = SettingsManager(db)

    # Get existing setting to preserve fields not being updated
    existing_settings = await manager.get_all(category)
    existing = existing_settings.get(category, {}).get(key)

    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Setting not found: {category}/{key}"
        )

    try:
        result = await manager.set(
            category=category,
            key=key,
            value=update.value,
            value_type=update.value_type or existing.get("value_type", "string"),
            description=update.description or existing.get("description"),
            is_sensitive=update.is_sensitive if update.is_sensitive is not None else existing.get("is_sensitive", False),
            validation_rules=update.validation_rules,
            updated_by="api",
        )

        # Broadcast change via WebSocket
        await broadcast_settings_change(category, key, str(update.value))

        return {
            "status": "updated",
            "category": result.category,
            "key": result.key,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a setting."""
    if not SettingsValidator.validate_category(category):
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    manager = SettingsManager(db)
    deleted = await manager.delete(category, key, deleted_by="api")

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Setting not found: {category}/{key}"
        )

    # Broadcast change via WebSocket
    await broadcast_settings_change(category, key, "DELETED")

    return {"status": "deleted", "category": category, "key": key}


@router.get("/history")
async def get_settings_history(
    category: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=1000),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get settings change history."""
    manager = SettingsManager(db)
    history = await manager.get_history(category, key, limit)
    return {"history": history}


@router.post("/import")
async def import_settings(
    data: SettingsImport,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Import settings from JSON."""
    manager = SettingsManager(db)
    count = await manager.import_settings(
        data.settings,
        imported_by="api",
        skip_sensitive=data.skip_sensitive,
    )
    return {"status": "imported", "count": count}


@router.get("/export")
async def export_settings(
    include_sensitive: bool = Query(default=False),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export all settings as JSON."""
    manager = SettingsManager(db)
    settings = await manager.export_settings(include_sensitive)
    return {"settings": settings}


@router.post("/reset")
async def reset_settings(
    category: Optional[str] = Query(None, description="Category to reset (None = all)"),
    confirm: bool = Query(False, description="Must be true to confirm reset"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset settings to defaults."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset settings"
        )

    manager = SettingsManager(db)
    count = await manager.reset_to_defaults(category, reset_by="api")

    return {"status": "reset", "count": count, "category": category or "all"}
