"""Error Handling Utilities for AWS Operations"""
import logging
import time
import functools
from typing import Callable, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def extract_client_error_details(error: ClientError) -> dict:
    """
    Extract error details from boto3 ClientError
    
    Args:
        error: ClientError exception
        
    Returns:
        Dictionary with error code, message, and request ID
    """
    error_response = error.response.get('Error', {})
    
    return {
        'error_code': error_response.get('Code', 'Unknown'),
        'error_message': error_response.get('Message', str(error)),
        'request_id': error.response.get('ResponseMetadata', {}).get('RequestId'),
        'http_status_code': error.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    }


def get_user_friendly_message(error: ClientError) -> str:
    """
    Generate user-friendly error message from ClientError
    
    Args:
        error: ClientError exception
        
    Returns:
        User-friendly error message string
    """
    error_code = error.response['Error']['Code']
    
    # Map AWS error codes to user-friendly messages
    error_messages = {
        'AccessDeniedException': 'Access denied. Please check your permissions.',
        'ResourceNotFoundException': 'The requested resource was not found.',
        'ThrottlingException': 'Service is temporarily busy. Please try again in a moment.',
        'ValidationException': 'Invalid request. Please check your input.',
        'InvalidParameterException': 'Invalid parameter provided.',
        'ServiceUnavailableException': 'Service is temporarily unavailable. Please try again later.',
        'InternalServerError': 'An internal error occurred. Please try again later.',
        'NotAuthorizedException': 'Authentication failed. Please check your credentials.',
        'UserNotFoundException': 'User not found.',
        'UsernameExistsException': 'This username is already taken.',
        'InvalidPasswordException': 'Password does not meet requirements.',
        'CodeMismatchException': 'Invalid verification code.',
        'ExpiredCodeException': 'Verification code has expired.',
        'TooManyRequestsException': 'Too many requests. Please slow down.',
        'LimitExceededException': 'Service limit exceeded.',
    }
    
    return error_messages.get(error_code, 'An error occurred. Please try again.')


def handle_aws_error(error: ClientError, operation: str) -> tuple[int, str]:
    """
    Handle AWS ClientError and return appropriate HTTP status code and message
    
    Args:
        error: ClientError exception
        operation: Name of the operation that failed
        
    Returns:
        Tuple of (http_status_code, user_message)
    """
    error_details = extract_client_error_details(error)
    error_code = error_details['error_code']
    
    logger.error(f"AWS operation '{operation}' failed", extra=error_details)
    
    # Map error codes to HTTP status codes
    if error_code in ['ResourceNotFoundException', 'UserNotFoundException']:
        return 404, get_user_friendly_message(error)
    elif error_code in ['AccessDeniedException', 'NotAuthorizedException']:
        return 403, get_user_friendly_message(error)
    elif error_code in ['ValidationException', 'InvalidParameterException', 'InvalidPasswordException']:
        return 400, get_user_friendly_message(error)
    elif error_code in ['ThrottlingException', 'TooManyRequestsException', 'LimitExceededException']:
        return 429, get_user_friendly_message(error)
    elif error_code in ['ServiceUnavailableException']:
        return 503, get_user_friendly_message(error)
    else:
        return 500, get_user_friendly_message(error)


def retry_with_exponential_backoff(max_retries: int = 3, base_delay: float = 0.5, 
                                   max_delay: float = 10.0, 
                                   retryable_errors: Optional[list] = None):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds between retries
        retryable_errors: List of error codes that should trigger retry (None = retry all throttling errors)
        
    Returns:
        Decorated function with retry logic
    """
    if retryable_errors is None:
        retryable_errors = [
            'ThrottlingException',
            'TooManyRequestsException',
            'ServiceUnavailableException',
            'InternalServerError',
            'RequestTimeout'
        ]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_count = 0
            last_error = None
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    last_error = e
                    
                    # Check if error is retryable
                    if error_code not in retryable_errors:
                        logger.warning(f"Non-retryable error in {func.__name__}: {error_code}")
                        raise
                    
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
                    
                    logger.warning(
                        f"Retrying {func.__name__} (attempt {retry_count}/{max_retries}) "
                        f"after {delay}s due to {error_code}"
                    )
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    # Non-ClientError exceptions are not retried
                    logger.error(f"Non-retryable exception in {func.__name__}: {type(e).__name__}")
                    raise
            
            # Should not reach here, but raise last error if we do
            if last_error:
                raise last_error
                
        return wrapper
    return decorator


class AWSServiceError(Exception):
    """Base exception for AWS service errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 status_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class AuthenticationError(AWSServiceError):
    """Exception for authentication failures"""
    pass


class ValidationError(AWSServiceError):
    """Exception for validation failures"""
    pass


class ResourceNotFoundError(AWSServiceError):
    """Exception for resource not found errors"""
    pass


class ServiceUnavailableError(AWSServiceError):
    """Exception for service unavailability"""
    pass
