"""Configuration Manager for AWS Services Integration"""
import os
import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration from environment variables and AWS Secrets Manager"""
    
    def __init__(self):
        """Initialize configuration manager"""
        self.region = os.getenv('AWS_REGION', 'ap-south-1')
        self._secrets_cache: Dict[str, Any] = {}
        self._secrets_client = None
        
        # Load environment variables
        self.config = {
            'aws_region': self.region,
            'cognito_user_pool_id': os.getenv('AWS_COGNITO_USER_POOL_ID'),
            'cognito_client_id': os.getenv('AWS_COGNITO_CLIENT_ID'),
            'cognito_client_secret': os.getenv('AWS_COGNITO_CLIENT_SECRET'),
            's3_audio_bucket': os.getenv('S3_AUDIO_BUCKET'),
            's3_pdf_bucket': os.getenv('S3_PDF_BUCKET'),
            'db_secret_name': os.getenv('DB_SECRET_NAME'),
            'flask_secret_name': os.getenv('FLASK_SECRET_NAME'),
            'jwt_secret_name': os.getenv('JWT_SECRET_NAME'),
            'database_url': os.getenv('DATABASE_URL'),
            'cors_allowed_origins': os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        }
        
        logger.info("Configuration loaded from environment variables")
    
    def _get_secrets_client(self):
        """Lazy initialization of Secrets Manager client"""
        if self._secrets_client is None:
            self._secrets_client = boto3.client('secretsmanager', region_name=self.region)
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
