"""Settings validation logic."""
import re
import json
from typing import Any, Optional

from pydantic import BaseModel, ValidationError


class ValidationResult(BaseModel):
    """Result of a validation check."""
    valid: bool
    error: Optional[str] = None
    coerced_value: Optional[Any] = None


class SettingsValidator:
    """Validate settings values against their rules."""

    @staticmethod
    def validate(
        value: str,
        value_type: str,
        validation_rules: Optional[dict] = None,
    ) -> ValidationResult:
        """
        Validate a setting value.

        Args:
            value: The string value to validate
            value_type: The expected type (string, integer, float, boolean, json)
            validation_rules: Optional rules for validation

        Returns:
            ValidationResult with validity status and any error message
        """
        if value is None or value == "":
            if validation_rules and validation_rules.get("required"):
                return ValidationResult(valid=False, error="Value is required")
            return ValidationResult(valid=True, coerced_value=None)

        # Type coercion and validation
        try:
            coerced = SettingsValidator._coerce_type(value, value_type)
        except ValueError as e:
            return ValidationResult(valid=False, error=str(e))

        # Apply validation rules
        if validation_rules:
            rule_result = SettingsValidator._validate_rules(
                coerced, value_type, validation_rules
            )
            if not rule_result.valid:
                return rule_result
            coerced = rule_result.coerced_value or coerced

        return ValidationResult(valid=True, coerced_value=coerced)

    @staticmethod
    def _coerce_type(value: str, value_type: str) -> Any:
        """Coerce string value to appropriate type."""
        if value_type == "integer":
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid integer")

        elif value_type == "float":
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid float")

        elif value_type == "boolean":
            lower = value.lower()
            if lower in ("true", "1", "yes", "on"):
                return True
            elif lower in ("false", "0", "no", "off"):
                return False
            else:
                raise ValueError(f"Value '{value}' is not a valid boolean")

        elif value_type == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Value is not valid JSON: {e}")

        # Default to string
        return value

    @staticmethod
    def _validate_rules(
        value: Any,
        value_type: str,
        rules: dict,
    ) -> ValidationResult:
        """Validate value against specific rules."""
        # Check minimum
        if "min" in rules and value_type in ("integer", "float"):
            if value < rules["min"]:
                return ValidationResult(
                    valid=False,
                    error=f"Value must be at least {rules['min']}"
                )

        # Check maximum
        if "max" in rules and value_type in ("integer", "float"):
            if value > rules["max"]:
                return ValidationResult(
                    valid=False,
                    error=f"Value must be at most {rules['max']}"
                )

        # Check enum
        if "enum" in rules:
            if value not in rules["enum"]:
                return ValidationResult(
                    valid=False,
                    error=f"Value must be one of: {', '.join(str(e) for e in rules['enum'])}"
                )

        # Check pattern (for strings)
        if "pattern" in rules and value_type == "string":
            if not re.match(rules["pattern"], str(value)):
                return ValidationResult(
                    valid=False,
                    error=f"Value does not match required pattern"
                )

        # Check min length
        if "min_length" in rules and value_type == "string":
            if len(str(value)) < rules["min_length"]:
                return ValidationResult(
                    valid=False,
                    error=f"Value must be at least {rules['min_length']} characters"
                )

        # Check max length
        if "max_length" in rules and value_type == "string":
            if len(str(value)) > rules["max_length"]:
                return ValidationResult(
                    valid=False,
                    error=f"Value must be at most {rules['max_length']} characters"
                )

        return ValidationResult(valid=True, coerced_value=value)

    @staticmethod
    def validate_category(category: str) -> bool:
        """Check if category is valid."""
        valid_categories = {
            "api_config",
            "agent_config",
            "risk_management",
            "scheduling",
            "performance",
            "ui_preferences",
            "system",
        }
        return category in valid_categories

    @staticmethod
    def validate_value_type(value_type: str) -> bool:
        """Check if value type is valid."""
        valid_types = {"string", "integer", "float", "boolean", "json"}
        return value_type in valid_types
