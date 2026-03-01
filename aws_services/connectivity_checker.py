"""
AWS Connectivity Checker
Validates connectivity to all required AWS services with timeout handling
"""
import logging
import time
from typing import Dict, Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError

logger = logging.getLogger(__name__)


class AWSConnectivityChecker:
    """Checks connectivity to AWS services with timeout protection"""
    
    def __init__(self, region: str, check_timeout: int = 10):
        """
        Initialize connectivity checker
        
        Args:
            region: AWS region to test
            check_timeout: Timeout in seconds for each individual check
        """
        self.region = region
        self.check_timeout = check_timeout
        self.results = {}
        # Configure boto3 with reasonable timeouts
        self._boto_config = Config(
            connect_timeout=check_timeout,
            read_timeout=check_timeout,
            retries={"max_attempts": 1, "mode": "standard"}
        )
    
    def check_cognito(self, user_pool_id: str, client_id: str) -> Dict[str, Any]:
        """
        Check Cognito connectivity
        
        Args:
            user_pool_id: Cognito User Pool ID
            client_id: Cognito Client ID
            
        Returns:
            Dict with status and details
        """
        start_time = time.time()
        
        try:
            client = boto3.client(
                'cognito-idp',
                region_name=self.region,
                config=self._boto_config
            )
            
            # Try to describe the user pool
            response = client.describe_user_pool(UserPoolId=user_pool_id)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'service': 'cognito-idp',
                'endpoint': f"cognito-idp.{self.region}.amazonaws.com",
                'duration_ms': round(duration_ms, 2),
                'user_pool_name': response['UserPool']['Name'],
                'message': 'Successfully connected to Cognito'
            }
            
        except EndpointConnectionError as e:
            return {
                'status': 'unhealthy',
                'service': 'cognito-idp',
                'endpoint': f"cognito-idp.{self.region}.amazonaws.com",
                'error': 'connection_failed',
                'message': f'Cannot connect to Cognito endpoint: {str(e)}'
            }
        except (ConnectTimeoutError, ReadTimeoutError) as e:
            return {
                'status': 'unhealthy',
                'service': 'cognito-idp',
                'endpoint': f"cognito-idp.{self.region}.amazonaws.com",
                'error': 'timeout',
                'message': f'Connection timed out after {self.check_timeout}s'
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                return {
                    'status': 'unhealthy',
                    'service': 'cognito-idp',
                    'error': 'resource_not_found',
                    'message': f'User pool {user_pool_id} not found'
                }
            return {
                'status': 'unhealthy',
                'service': 'cognito-idp',
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'cognito-idp',
                'error': 'unexpected_error',
                'message': str(e)
            }
    
    def check_s3(self, bucket_name: str) -> Dict[str, Any]:
        """
        Check S3 connectivity
        
        Args:
            bucket_name: S3 bucket name
            
        Returns:
            Dict with status and details
        """
        start_time = time.time()
        
        try:
            client = boto3.client(
                's3',
                region_name=self.region,
                config=self._boto_config
            )
            
            # Try to get bucket location
            client.get_bucket_location(Bucket=bucket_name)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'service': 's3',
                'endpoint': f"s3.{self.region}.amazonaws.com",
                'duration_ms': round(duration_ms, 2),
                'bucket': bucket_name,
                'message': 'Successfully connected to S3'
            }
            
        except EndpointConnectionError as e:
            return {
                'status': 'unhealthy',
                'service': 's3',
                'endpoint': f"s3.{self.region}.amazonaws.com",
                'error': 'connection_failed',
                'message': f'Cannot connect to S3 endpoint: {str(e)}'
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NoSuchBucket', '404']:
                return {
                    'status': 'unhealthy',
                    'service': 's3',
                    'error': 'bucket_not_found',
                    'message': f'Bucket {bucket_name} not found'
                }
            return {
                'status': 'unhealthy',
                'service': 's3',
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 's3',
                'error': 'unexpected_error',
                'message': str(e)
            }
    
    def check_transcribe(self) -> Dict[str, Any]:
        """
        Check Transcribe connectivity
        
        Returns:
            Dict with status and details
        """
        start_time = time.time()
        
        try:
            client = boto3.client(
                'transcribe',
                region_name=self.region,
                config=self._boto_config
            )
            
            # Try to list transcription jobs (limit 1)
            client.list_transcription_jobs(MaxResults=1)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'service': 'transcribe',
                'endpoint': f"transcribe.{self.region}.amazonaws.com",
                'duration_ms': round(duration_ms, 2),
                'message': 'Successfully connected to Transcribe'
            }
            
        except EndpointConnectionError as e:
            return {
                'status': 'unhealthy',
                'service': 'transcribe',
                'endpoint': f"transcribe.{self.region}.amazonaws.com",
                'error': 'connection_failed',
                'message': f'Cannot connect to Transcribe endpoint: {str(e)}'
            }
        except ClientError as e:
            return {
                'status': 'unhealthy',
                'service': 'transcribe',
                'error': e.response['Error']['Code'],
                'message': str(e)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'transcribe',
                'error': 'unexpected_error',
                'message': str(e)
            }
    
    def check_comprehend(self, region_override: str = None) -> Dict[str, Any]:
        """
        Check Comprehend Medical connectivity
        
        Returns:
            Dict with status and details
        """
        start_time = time.time()
        region = region_override or self.region
        
        try:
            client = boto3.client(
                'comprehendmedical',
                region_name=region,
                config=self._boto_config
            )
            
            # Try a simple entity detection with minimal text
            client.detect_entities_v2(Text="test")
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'service': 'comprehendmedical',
                'endpoint': f"comprehendmedical.{region}.amazonaws.com",
                'duration_ms': round(duration_ms, 2),
                'message': 'Successfully connected to Comprehend Medical'
            }
            
        except EndpointConnectionError as e:
            return {
                'status': 'unhealthy',
                'service': 'comprehendmedical',
                'endpoint': f"comprehendmedical.{region}.amazonaws.com",
                'error': 'connection_failed',
                'message': f'Cannot connect to Comprehend Medical endpoint: {str(e)}'
            }
        except ClientError as e:
            return {
                'status': 'unhealthy',
                'service': 'comprehendmedical',
                'error': e.response['Error']['Code'],
                'message': str(e)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'comprehendmedical',
                'error': 'unexpected_error',
                'message': str(e)
            }
    
    def check_secrets_manager(self, secret_name: str) -> Dict[str, Any]:
        """
        Check Secrets Manager connectivity
        
        Args:
            secret_name: Secret name to test
            
        Returns:
            Dict with status and details
        """
        start_time = time.time()
        
        try:
            client = boto3.client(
                'secretsmanager',
                region_name=self.region,
                config=self._boto_config
            )
            
            # Try to describe the secret
            client.describe_secret(SecretId=secret_name)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'service': 'secretsmanager',
                'endpoint': f"secretsmanager.{self.region}.amazonaws.com",
                'duration_ms': round(duration_ms, 2),
                'message': 'Successfully connected to Secrets Manager'
            }
            
        except EndpointConnectionError as e:
            return {
                'status': 'unhealthy',
                'service': 'secretsmanager',
                'endpoint': f"secretsmanager.{self.region}.amazonaws.com",
                'error': 'connection_failed',
                'message': f'Cannot connect to Secrets Manager endpoint: {str(e)}'
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                return {
                    'status': 'unhealthy',
                    'service': 'secretsmanager',
                    'error': 'secret_not_found',
                    'message': f'Secret {secret_name} not found'
                }
            return {
                'status': 'unhealthy',
                'service': 'secretsmanager',
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'secretsmanager',
                'error': 'unexpected_error',
                'message': str(e)
            }
    
    def run_all_checks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all connectivity checks with timeout protection
        
        Args:
            config: Configuration dict with service details
            
        Returns:
            Dict with all check results
        """
        logger.info("Running AWS connectivity checks...")
        
        results = {
            'overall_status': 'healthy',
            'timestamp': time.time(),
            'region': self.region,
            'checks': {}
        }
        
        # Check Cognito
        if config.get('cognito_user_pool_id') and config.get('cognito_client_id'):
            results['checks']['cognito'] = self.check_cognito(
                config['cognito_user_pool_id'],
                config['cognito_client_id']
            )
            if results['checks']['cognito']['status'] != 'healthy':
                results['overall_status'] = 'unhealthy'
        
        # Check S3 Audio Bucket
        if config.get('s3_audio_bucket'):
            results['checks']['s3_audio'] = self.check_s3(config['s3_audio_bucket'])
            if results['checks']['s3_audio']['status'] != 'healthy':
                results['overall_status'] = 'unhealthy'
        
        # Check S3 PDF Bucket
        if config.get('s3_pdf_bucket'):
            results['checks']['s3_pdf'] = self.check_s3(config['s3_pdf_bucket'])
            if results['checks']['s3_pdf']['status'] != 'healthy':
                results['overall_status'] = 'unhealthy'
        
        # Check Transcribe
        results['checks']['transcribe'] = self.check_transcribe()
        if results['checks']['transcribe']['status'] != 'healthy':
            results['overall_status'] = 'unhealthy'
        
        # Check Comprehend Medical (optional, region-dependent)
        if config.get('enable_comprehend_medical', True):
            results['checks']['comprehend'] = self.check_comprehend(
                config.get('comprehend_region')
            )
            if results['checks']['comprehend']['status'] != 'healthy':
                results['overall_status'] = 'unhealthy'
        else:
            results['checks']['comprehend'] = {
                'status': 'skipped',
                'service': 'comprehendmedical',
                'message': 'Comprehend Medical checks disabled by configuration'
            }
        
        # Check Secrets Manager
        if config.get('db_secret_name'):
            results['checks']['secrets_manager'] = self.check_secrets_manager(
                config['db_secret_name']
            )
            if results['checks']['secrets_manager']['status'] != 'healthy':
                results['overall_status'] = 'unhealthy'
        
        logger.info(f"AWS connectivity checks completed: {results['overall_status']}")
        
        return results
