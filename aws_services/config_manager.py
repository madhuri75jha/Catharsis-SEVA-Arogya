"""Configuration Manager for AWS Services Integration"""
import os
import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration from environment variables and AWS Secrets Manager"""
    
    def __init__(self):
        """Initialize configuration manager"""
        self.region = os.getenv('AWS_REGION', 'ap-south-1')
        self._secrets_cache: Dict[str, Any] = {}
        self._secrets_client = None
        
        def _parse_int(value: Optional[str], default: int, minimum: int = 1, maximum: int = 60) -> int:
            """Parse int from env with bounds."""
            if value is None or value == "":
                return default
            try:
                parsed = int(value)
            except ValueError:
                return default
            if parsed < minimum:
                return minimum
            if parsed > maximum:
                return maximum
            return parsed

        # Load environment variables
        self.config = {
            'aws_region': self.region,
            'aws_comprehend_region': os.getenv('AWS_COMPREHEND_REGION', self.region),
            'bedrock_region': os.getenv('BEDROCK_REGION', 'us-east-1'),
            # Default to Claude 3 Haiku for lower cost while keeping tool/function support.
            'bedrock_model_id': os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0'),
            'cognito_user_pool_id': os.getenv('AWS_COGNITO_USER_POOL_ID'),
            'cognito_client_id': os.getenv('AWS_COGNITO_CLIENT_ID'),
            'cognito_client_secret': os.getenv('AWS_COGNITO_CLIENT_SECRET'),
            's3_audio_bucket': os.getenv('S3_AUDIO_BUCKET'),
            's3_pdf_bucket': os.getenv('S3_PDF_BUCKET'),
            'db_secret_name': os.getenv('DB_SECRET_NAME'),
            'flask_secret_name': os.getenv('FLASK_SECRET_NAME'),
            'jwt_secret_name': os.getenv('JWT_SECRET_NAME'),
            'database_url': os.getenv('DATABASE_URL'),
            'db_host': os.getenv('DB_HOST'),
            'db_port': os.getenv('DB_PORT'),
            'db_username': os.getenv('DB_USERNAME'),
            'db_password': os.getenv('DB_PASSWORD'),
            'db_name': os.getenv('DB_NAME'),
            'flask_secret_key': os.getenv('FLASK_SECRET_KEY'),
            'jwt_secret': os.getenv('JWT_SECRET'),
            'cors_allowed_origins': os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'enable_comprehend_medical': os.getenv('ENABLE_COMPREHEND_MEDICAL', 'true').lower() in ('1', 'true', 'yes'),
            # Keep health checks under typical ALB idle timeout (60s)
            'aws_connectivity_check_timeout': _parse_int(
                os.getenv('AWS_CONNECTIVITY_CHECK_TIMEOUT'),
                default=5,
                minimum=1,
                maximum=20
            ),
        }
        
        logger.info("Configuration loaded from environment variables")
    
    def _get_secrets_client(self):
        """Lazy initialization of Secrets Manager client"""
        if self._secrets_client is None:
            # Keep Secrets Manager calls from blocking app startup too long
            client_config = Config(
                connect_timeout=3,
                read_timeout=5,
                retries={"max_attempts": 2}
            )
            self._secrets_client = boto3.client(
                'secretsmanager',
                region_name=self.region,
                config=client_config
            )
        return self._secrets_client
    
    def get_secret(self, secret_name: str, fallback_env_var: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve secret from AWS Secrets Manager with caching and fallback
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            fallback_env_var: Environment variable to use as fallback
            
        Returns:
            Secret value (string or dict) or None if not found
        """
        # Check cache first
        if secret_name in self._secrets_cache:
            logger.debug(f"Retrieved secret '{secret_name}' from cache")
            return self._secrets_cache[secret_name]
        
        # Try to retrieve from Secrets Manager
        try:
            client = self._get_secrets_client()
            response = client.get_secret_value(SecretId=secret_name)
            
            # Parse secret value
            if 'SecretString' in response:
                secret_value = response['SecretString']
                try:
                    # Try to parse as JSON
                    secret_data = json.loads(secret_value)
                except json.JSONDecodeError:
                    # Plain string secret
                    secret_data = secret_value
                
                # Cache the secret
                self._secrets_cache[secret_name] = secret_data
                logger.info(f"Retrieved secret '{secret_name}' from Secrets Manager")
                return secret_data
            else:
                logger.warning(f"Secret '{secret_name}' has no SecretString")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.warning(f"Failed to retrieve secret '{secret_name}' from Secrets Manager: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret '{secret_name}': {str(e)}")
        
        # Fallback to environment variable
        if fallback_env_var:
            fallback_value = os.getenv(fallback_env_var)
            if fallback_value:
                logger.info(f"Using fallback environment variable '{fallback_env_var}' for secret '{secret_name}'")
                return fallback_value
        
        return None
    
    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """
        Retrieve database credentials from Secrets Manager or environment
        
        Returns:
            Dictionary with database connection parameters or None
        """
        # Prefer directly provided environment variables (e.g. injected by ECS)
        if self.config.get('db_host') and self.config.get('db_username') and self.config.get('db_password'):
            return {
                'host': self.config.get('db_host'),
                'port': int(self.config.get('db_port') or 5432),
                'username': self.config.get('db_username'),
                'password': self.config.get('db_password'),
                'database': self.config.get('db_name') or 'seva_arogya'
            }

        db_secret_name = self.config.get('db_secret_name')
        if db_secret_name:
            secret = self.get_secret(db_secret_name)
            if secret and isinstance(secret, dict):
                return secret
        
        # Fallback to DATABASE_URL environment variable
        database_url = self.config.get('database_url')
        if database_url:
            logger.info("Using DATABASE_URL from environment as fallback")
            return {'database_url': database_url}
        
        return None
    
    def get_flask_secret_key(self) -> Optional[str]:
        """
        Retrieve Flask secret key from Secrets Manager or environment
        
        Returns:
            Flask secret key string or None
        """
        if self.config.get('flask_secret_key'):
            return self.config.get('flask_secret_key')

        flask_secret_name = self.config.get('flask_secret_name')
        if flask_secret_name:
            secret = self.get_secret(flask_secret_name, fallback_env_var='SECRET_KEY')
            if secret:
                return secret if isinstance(secret, str) else secret.get('secret_key')
        
        return os.getenv('SECRET_KEY')
    
    def get_jwt_secret(self) -> Optional[str]:
        """
        Retrieve JWT secret from Secrets Manager or environment
        
        Returns:
            JWT secret string or None
        """
        if self.config.get('jwt_secret'):
            return self.config.get('jwt_secret')

        jwt_secret_name = self.config.get('jwt_secret_name')
        if jwt_secret_name:
            secret = self.get_secret(jwt_secret_name)
            if secret:
                return secret if isinstance(secret, str) else secret.get('jwt_secret')
        
        # Fallback to Flask secret key
        return self.get_flask_secret_key()
    
    def validate_required_config(self) -> bool:
        """
        Validate that all required configuration values are present
        
        Returns:
            True if all required config is present, False otherwise
        """
        required_keys = [
            'aws_region',
            'cognito_user_pool_id',
            'cognito_client_id',
            's3_audio_bucket',
            's3_pdf_bucket',
        ]
        
        missing_keys = []
        for key in required_keys:
            if not self.config.get(key):
                missing_keys.append(key)
        
        if missing_keys:
            logger.error(f"Missing required configuration: {', '.join(missing_keys)}")
            return False
        
        # Validate database credentials
        db_creds = self.get_database_credentials()
        if not db_creds:
            logger.error("Missing database credentials (DB_SECRET_NAME or DATABASE_URL)")
            return False
        
        # Validate Flask secret key
        flask_secret = self.get_flask_secret_key()
        if not flask_secret:
            logger.error("Missing Flask secret key (FLASK_SECRET_NAME or SECRET_KEY)")
            return False
        
        logger.info("All required configuration validated successfully")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self.config.get(key, default)


# Hospital Configuration Management
from pathlib import Path
from models.bedrock_extraction import HospitalConfiguration
from pydantic import ValidationError


class ConfigurationNotFoundError(Exception):
    """Raised when hospital configuration is not found"""
    pass


class ConfigurationValidationError(Exception):
    """Raised when hospital configuration is invalid"""
    pass


# Add these methods to ConfigManager class (monkey-patch for now)
def _init_hospital_config(self):
    """Initialize hospital configuration cache"""
    if not hasattr(self, '_hospital_config_cache'):
        self._hospital_config_cache = {}
        self._hospital_config_dir = Path('config/hospitals')


def load_hospital_configuration(self, hospital_id: str) -> HospitalConfiguration:
    """
    Load and validate hospital configuration from JSON file
    
    Args:
        hospital_id: Hospital identifier
        
    Returns:
        Validated HospitalConfiguration object
        
    Raises:
        ConfigurationNotFoundError: If configuration file doesn't exist
        ConfigurationValidationError: If configuration is invalid
    """
    self._init_hospital_config()
    
    # Check cache first
    if hospital_id in self._hospital_config_cache:
        logger.debug(f"Retrieved hospital config '{hospital_id}' from cache")
        return self._hospital_config_cache[hospital_id]
    
    # Build file path
    config_file = self._hospital_config_dir / f"{hospital_id}.json"
    
    if not config_file.exists():
        logger.warning(f"Hospital configuration file not found: {config_file}")
        raise ConfigurationNotFoundError(
            f"Hospital configuration not found for hospital_id: {hospital_id}"
        )
    
    try:
        # Load JSON file
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Validate using Pydantic model
        hospital_config = self.validate_hospital_configuration(config_data)
        
        # Cache the validated configuration
        self._hospital_config_cache[hospital_id] = hospital_config
        
        logger.info(f"Loaded and validated hospital configuration for '{hospital_id}'")
        return hospital_config
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in hospital configuration file {config_file}: {e}")
        raise ConfigurationValidationError(
            f"Invalid JSON in configuration file for {hospital_id}: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Error loading hospital configuration for {hospital_id}: {e}")
        raise


def get_default_hospital_configuration(self) -> HospitalConfiguration:
    """
    Get default hospital configuration
    
    Returns:
        Default HospitalConfiguration object
        
    Raises:
        ConfigurationNotFoundError: If default configuration doesn't exist
    """
    return self.load_hospital_configuration('default')


def validate_hospital_configuration(self, config_dict: dict) -> HospitalConfiguration:
    """
    Validate hospital configuration structure using Pydantic
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        Validated HospitalConfiguration object
        
    Raises:
        ConfigurationValidationError: If configuration is invalid
    """
    try:
        hospital_config = HospitalConfiguration(**config_dict)
        logger.debug(f"Validated hospital configuration for '{hospital_config.hospital_id}'")
        return hospital_config
    except ValidationError as e:
        logger.error(f"Hospital configuration validation failed: {e}")
        raise ConfigurationValidationError(
            f"Invalid hospital configuration: {str(e)}"
        ) from e


def invalidate_hospital_config_cache(self, hospital_id: Optional[str] = None):
    """
    Invalidate hospital configuration cache for hot-reload
    
    Args:
        hospital_id: Specific hospital ID to invalidate, or None to clear all
    """
    self._init_hospital_config()
    
    if hospital_id:
        if hospital_id in self._hospital_config_cache:
            del self._hospital_config_cache[hospital_id]
            logger.info(f"Invalidated cache for hospital config '{hospital_id}'")
    else:
        self._hospital_config_cache.clear()
        logger.info("Cleared all hospital configuration cache")


# Monkey-patch the methods onto ConfigManager
ConfigManager._init_hospital_config = _init_hospital_config
ConfigManager.load_hospital_configuration = load_hospital_configuration
ConfigManager.get_default_hospital_configuration = get_default_hospital_configuration
ConfigManager.validate_hospital_configuration = validate_hospital_configuration
ConfigManager.invalidate_hospital_config_cache = invalidate_hospital_config_cache
