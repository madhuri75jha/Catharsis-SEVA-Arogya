"""Base AWS Client Manager"""
import logging
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAWSClient:
    """Base class for AWS service clients with common initialization and error handling"""
    
    def __init__(self, service_name: str, region: str):
        """
        Initialize AWS service client
        
        Args:
            service_name: AWS service name (e.g., 's3', 'cognito-idp', 'transcribe')
            region: AWS region name
            
        Raises:
            Exception: If client initialization fails
        """
        self.service_name = service_name
        self.region = region
        self.client = None
        
        try:
            logger.info(f"Initializing {service_name} client in region {region}")
            self.client = boto3.client(service_name, region_name=region)
            logger.info(f"Successfully initialized {service_name} client")
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to initialize {service_name} client: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error initializing {service_name} client: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _log_operation(self, operation: str, **kwargs):
        """Log AWS operation with service name and parameters"""
        logger.info(f"{self.service_name}.{operation}", extra={
            'service': self.service_name,
            'operation': operation,
            'region': self.region
        })
    
    def _log_error(self, operation: str, error: Exception, **kwargs):
        """Log AWS operation error with details"""
        error_details = {
            'service': self.service_name,
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        # Extract request ID if available
        if isinstance(error, ClientError):
            error_details['error_code'] = error.response['Error']['Code']
            error_details['request_id'] = error.response.get('ResponseMetadata', {}).get('RequestId')
        
        logger.error(f"{self.service_name}.{operation} failed", extra=error_details)
    
    def _log_success(self, operation: str, duration_ms: Optional[float] = None, **kwargs):
        """Log successful AWS operation with duration"""
        log_data = {
            'service': self.service_name,
            'operation': operation,
            'status': 'success'
        }
        
        if duration_ms is not None:
            log_data['duration_ms'] = duration_ms
        
        logger.info(f"{self.service_name}.{operation} succeeded", extra=log_data)
