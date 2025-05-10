"""
Config Validator for CryptoBot.

This module provides the ConfigValidator class, which validates configuration values,
ensures required settings are present, performs type checking and range validation,
validates dependencies between config values, and provides helpful error messages
for invalid configurations.
"""

import logging
import re
import json
import os
from typing import Dict, List, Any, Optional, Union, Callable, Set, Tuple
from jsonschema import validate, ValidationError, Draft7Validator, validators

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of a configuration validation."""
    
    def __init__(self, valid: bool, errors: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize a validation result.
        
        Args:
            valid: Whether the configuration is valid
            errors: List of validation errors
        """
        self.valid = valid
        self.errors = errors or []
    
    def add_error(self, path: str, message: str, value: Any = None) -> None:
        """
        Add a validation error.
        
        Args:
            path: Path to the invalid configuration value
            message: Error message
            value: Invalid value
        """
        self.errors.append({
            "path": path,
            "message": message,
            "value": value
        })
        self.valid = False
    
    def merge(self, other: 'ValidationResult') -> None:
        """
        Merge with another validation result.
        
        Args:
            other: Other validation result
        """
        if not other.valid:
            self.valid = False
            self.errors.extend(other.errors)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "valid": self.valid,
            "errors": self.errors
        }
    
    def __bool__(self) -> bool:
        """
        Convert to a boolean.
        
        Returns:
            bool: True if valid, False otherwise
        """
        return self.valid


class ConfigValidator:
    """
    Validator for configuration values.
    
    The ConfigValidator validates configuration values, ensures required settings are present,
    performs type checking and range validation, validates dependencies between config values,
    and provides helpful error messages for invalid configurations.
    """
    
    def __init__(self):
        """Initialize the config validator."""
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._custom_validators: Dict[str, Callable[[Any], Tuple[bool, Optional[str]]]] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        logger.info("Config Validator initialized")
    
    def add_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """
        Add a JSON schema for validation.
        
        Args:
            name: Schema name
            schema: JSON schema
        """
        self._schemas[name] = schema
        logger.info(f"Added schema '{name}'")
    
    def add_schema_from_file(self, name: str, file_path: str) -> None:
        """
        Add a JSON schema from a file.
        
        Args:
            name: Schema name
            file_path: Path to the schema file
        
        Raises:
            FileNotFoundError: If the schema file does not exist
            json.JSONDecodeError: If the schema file is not valid JSON
        """
        with open(file_path, "r") as f:
            schema = json.load(f)
        
        self.add_schema(name, schema)
        logger.info(f"Added schema '{name}' from {file_path}")
    
    def add_custom_validator(self, name: str, validator: Callable[[Any], Tuple[bool, Optional[str]]]) -> None:
        """
        Add a custom validator function.
        
        Args:
            name: Validator name
            validator: Validator function that takes a value and returns (valid, error_message)
        """
        self._custom_validators[name] = validator
        logger.info(f"Added custom validator '{name}'")
    
    def add_dependency(self, key: str, depends_on: str) -> None:
        """
        Add a dependency between configuration values.
        
        Args:
            key: Configuration key
            depends_on: Key that this key depends on
        """
        if key not in self._dependencies:
            self._dependencies[key] = set()
        
        self._dependencies[key].add(depends_on)
        logger.info(f"Added dependency: {key} depends on {depends_on}")
    
    def validate_schema(self, config: Dict[str, Any], schema_name: str) -> ValidationResult:
        """
        Validate a configuration against a JSON schema.
        
        Args:
            config: Configuration to validate
            schema_name: Name of the schema to use
        
        Returns:
            ValidationResult: Validation result
        
        Raises:
            ValueError: If the schema does not exist
        """
        if schema_name not in self._schemas:
            raise ValueError(f"Schema '{schema_name}' does not exist")
        
        schema = self._schemas[schema_name]
        result = ValidationResult(True)
        
        try:
            validate(instance=config, schema=schema)
        except ValidationError as e:
            result.add_error(
                path=".".join(str(p) for p in e.path),
                message=e.message,
                value=e.instance
            )
        
        return result
    
    def validate_with_custom_validator(self, value: Any, validator_name: str) -> ValidationResult:
        """
        Validate a value with a custom validator.
        
        Args:
            value: Value to validate
            validator_name: Name of the validator to use
        
        Returns:
            ValidationResult: Validation result
        
        Raises:
            ValueError: If the validator does not exist
        """
        if validator_name not in self._custom_validators:
            raise ValueError(f"Validator '{validator_name}' does not exist")
        
        validator = self._custom_validators[validator_name]
        result = ValidationResult(True)
        
        valid, error_message = validator(value)
        if not valid:
            result.add_error(
                path="",
                message=error_message or f"Invalid value for validator '{validator_name}'",
                value=value
            )
        
        return result
    
    def validate_type(self, value: Any, expected_type: Union[type, List[type]], path: str = "") -> ValidationResult:
        """
        Validate the type of a value.
        
        Args:
            value: Value to validate
            expected_type: Expected type or list of types
            path: Path to the value in the configuration
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        if isinstance(expected_type, list):
            if not any(isinstance(value, t) for t in expected_type):
                type_names = [t.__name__ for t in expected_type]
                result.add_error(
                    path=path,
                    message=f"Expected one of types {type_names}, got {type(value).__name__}",
                    value=value
                )
        else:
            if not isinstance(value, expected_type):
                result.add_error(
                    path=path,
                    message=f"Expected type {expected_type.__name__}, got {type(value).__name__}",
                    value=value
                )
        
        return result
    
    def validate_range(self, value: Union[int, float], min_value: Optional[Union[int, float]] = None,
                      max_value: Optional[Union[int, float]] = None, path: str = "") -> ValidationResult:
        """
        Validate that a numeric value is within a range.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            path: Path to the value in the configuration
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        if not isinstance(value, (int, float)):
            result.add_error(
                path=path,
                message=f"Expected numeric value, got {type(value).__name__}",
                value=value
            )
            return result
        
        if min_value is not None and value < min_value:
            result.add_error(
                path=path,
                message=f"Value {value} is less than minimum {min_value}",
                value=value
            )
        
        if max_value is not None and value > max_value:
            result.add_error(
                path=path,
                message=f"Value {value} is greater than maximum {max_value}",
                value=value
            )
        
        return result
    
    def validate_string(self, value: str, pattern: Optional[str] = None, min_length: Optional[int] = None,
                       max_length: Optional[int] = None, path: str = "") -> ValidationResult:
        """
        Validate a string value.
        
        Args:
            value: Value to validate
            pattern: Regular expression pattern
            min_length: Minimum length
            max_length: Maximum length
            path: Path to the value in the configuration
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        if not isinstance(value, str):
            result.add_error(
                path=path,
                message=f"Expected string, got {type(value).__name__}",
                value=value
            )
            return result
        
        if pattern is not None:
            if not re.match(pattern, value):
                result.add_error(
                    path=path,
                    message=f"String '{value}' does not match pattern '{pattern}'",
                    value=value
                )
        
        if min_length is not None and len(value) < min_length:
            result.add_error(
                path=path,
                message=f"String length {len(value)} is less than minimum {min_length}",
                value=value
            )
        
        if max_length is not None and len(value) > max_length:
            result.add_error(
                path=path,
                message=f"String length {len(value)} is greater than maximum {max_length}",
                value=value
            )
        
        return result
    
    def validate_enum(self, value: Any, allowed_values: List[Any], path: str = "") -> ValidationResult:
        """
        Validate that a value is one of a set of allowed values.
        
        Args:
            value: Value to validate
            allowed_values: List of allowed values
            path: Path to the value in the configuration
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        if value not in allowed_values:
            result.add_error(
                path=path,
                message=f"Value '{value}' is not one of the allowed values: {allowed_values}",
                value=value
            )
        
        return result
    
    def validate_dependencies(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate dependencies between configuration values.
        
        Args:
            config: Configuration to validate
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        for key, depends_on in self._dependencies.items():
            # Check if the key exists in the configuration
            key_parts = key.split(".")
            key_exists = True
            key_value = config
            
            for part in key_parts:
                if isinstance(key_value, dict) and part in key_value:
                    key_value = key_value[part]
                else:
                    key_exists = False
                    break
            
            if not key_exists:
                continue
            
            # Check if all dependencies exist
            for dep in depends_on:
                dep_parts = dep.split(".")
                dep_exists = True
                dep_value = config
                
                for part in dep_parts:
                    if isinstance(dep_value, dict) and part in dep_value:
                        dep_value = dep_value[part]
                    else:
                        dep_exists = False
                        break
                
                if not dep_exists:
                    result.add_error(
                        path=key,
                        message=f"Depends on '{dep}', which does not exist",
                        value=key_value
                    )
        
        return result
    
    def validate_required_keys(self, config: Dict[str, Any], required_keys: List[str]) -> ValidationResult:
        """
        Validate that required keys exist in the configuration.
        
        Args:
            config: Configuration to validate
            required_keys: List of required keys (dot-separated for nested keys)
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        for key in required_keys:
            key_parts = key.split(".")
            key_exists = True
            key_value = config
            
            for part in key_parts:
                if isinstance(key_value, dict) and part in key_value:
                    key_value = key_value[part]
                else:
                    key_exists = False
                    break
            
            if not key_exists:
                result.add_error(
                    path=key,
                    message=f"Required key '{key}' is missing"
                )
        
        return result
    
    def validate_config(self, config: Dict[str, Any], schema_name: Optional[str] = None) -> ValidationResult:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate
            schema_name: Name of the schema to use, or None to skip schema validation
        
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(True)
        
        # Validate against schema if provided
        if schema_name is not None:
            schema_result = self.validate_schema(config, schema_name)
            result.merge(schema_result)
        
        # Validate dependencies
        dep_result = self.validate_dependencies(config)
        result.merge(dep_result)
        
        return result
    
    def extend_with_default(self, validator_class):
        """
        Extend a JSON Schema validator to fill in default values.
        
        Args:
            validator_class: Validator class to extend
        
        Returns:
            type: Extended validator class
        """
        validate_properties = validator_class.VALIDATORS["properties"]
        
        def set_defaults(validator, properties, instance, schema):
            for property, subschema in properties.items():
                if "default" in subschema and instance.get(property) is None:
                    instance[property] = subschema["default"]
            
            for error in validate_properties(validator, properties, instance, schema):
                yield error
        
        return validators.extend(validator_class, {"properties": set_defaults})
    
    def apply_defaults(self, config: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """
        Apply default values from a schema to a configuration.
        
        Args:
            config: Configuration to update
            schema_name: Name of the schema to use
        
        Returns:
            Dict[str, Any]: Updated configuration
        
        Raises:
            ValueError: If the schema does not exist
        """
        if schema_name not in self._schemas:
            raise ValueError(f"Schema '{schema_name}' does not exist")
        
        schema = self._schemas[schema_name]
        
        # Create a copy of the configuration
        config_copy = json.loads(json.dumps(config))
        
        # Create a validator that fills in default values
        DefaultValidatingDraft7Validator = self.extend_with_default(Draft7Validator)
        
        # Apply defaults
        validator = DefaultValidatingDraft7Validator(schema)
        validator.validate(config_copy)
        
        return config_copy
    
    def generate_config_template(self, schema_name: str) -> Dict[str, Any]:
        """
        Generate a configuration template from a schema.
        
        Args:
            schema_name: Name of the schema to use
        
        Returns:
            Dict[str, Any]: Configuration template
        
        Raises:
            ValueError: If the schema does not exist
        """
        if schema_name not in self._schemas:
            raise ValueError(f"Schema '{schema_name}' does not exist")
        
        schema = self._schemas[schema_name]
        
        # Start with an empty configuration
        config = {}
        
        # Apply defaults
        return self.apply_defaults(config, schema_name)