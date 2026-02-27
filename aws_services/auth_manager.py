"""Authentication Manager for AWS Cognito"""
import logging
import time
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class AuthManager(BaseAWSClient):
    """Manages AWS Cognito authentication operations"""
    
    def __init__(self, region: str, user_pool_id: str, client_id: str, client_secret: Optional[str] = None):
        """
        Initialize Auth Manager
        
        Args:
            region: AWS region
            user_pool_id: Cognito User Pool ID
            client_id: Cognito App Client ID
            client_secret: Cognito App Client Secret (optional)
        """
        super().__init__('cognito-idp', region)
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        logger.info(f"Auth manager initialized with user_pool_id={user_pool_id}")
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with Cognito using USER_PASSWORD_AUTH flow
        
        Args:
            username: User's email/username
            password: User's password
            
        Returns:
            Dictionary with tokens (access_token, id_token, refresh_token) or None
        """
        start_time = time.time()
        
        try:
            self._log_operation('authenticate', username=username)
            
            auth_params = {
                'USERNAME': username,
                'PASSWORD': password
            }
            
            # Add SECRET_HASH if client secret is configured
            if self.client_secret:
                import hmac
                import hashlib
                import base64
                message = bytes(username + self.client_id, 'utf-8')
                secret = bytes(self.client_secret, 'utf-8')
                secret_hash = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest()).decode()
                auth_params['SECRET_HASH'] = secret_hash
            
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters=auth_params
            )
            
            if 'AuthenticationResult' in response:
                auth_result = response['AuthenticationResult']
                tokens = {
                    'access_token': auth_result.get('AccessToken'),
                    'id_token': auth_result.get('IdToken'),
                    'refresh_token': auth_result.get('RefreshToken'),
                    'expires_in': auth_result.get('ExpiresIn'),
                    'token_type': auth_result.get('TokenType')
                }
                
                duration_ms = (time.time() - start_time) * 1000
                self._log_success('authenticate', duration_ms=duration_ms, username=username)
                logger.info(f"User authenticated successfully: {username}")
                
                return tokens
            else:
                logger.warning(f"Authentication response missing AuthenticationResult for user: {username}")
                return None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self._log_error('authenticate', e, username=username)
            
            # Log authentication failure without exposing sensitive details
            if error_code == 'NotAuthorizedException':
                logger.warning(f"Authentication failed for user {username}: Invalid credentials")
            elif error_code == 'UserNotFoundException':
                logger.warning(f"Authentication failed for user {username}: User not found")
            elif error_code == 'UserNotConfirmedException':
                logger.warning(f"Authentication failed for user {username}: User not confirmed")
            else:
                logger.error(f"Authentication failed for user {username}: {error_code}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            return None
    
    def register(self, email: str, password: str, attributes: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Register new user in Cognito
        
        Args:
            email: User's email (used as username)
            password: User's password
            attributes: Additional user attributes (name, phone, etc.)
            
        Returns:
            Dictionary with user_sub and confirmation status or None
        """
        start_time = time.time()
        
        try:
            self._log_operation('register', email=email)
            
            # Build user attributes
            user_attributes = [
                {'Name': 'email', 'Value': email}
            ]
            
            if attributes:
                for key, value in attributes.items():
                    user_attributes.append({'Name': key, 'Value': value})
            
            # Add SECRET_HASH if client secret is configured
            secret_hash = None
            if self.client_secret:
                import hmac
                import hashlib
                import base64
                message = bytes(email + self.client_id, 'utf-8')
                secret = bytes(self.client_secret, 'utf-8')
                secret_hash = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest()).decode()
            
            sign_up_params = {
                'ClientId': self.client_id,
                'Username': email,
                'Password': password,
                'UserAttributes': user_attributes
            }
            
            if secret_hash:
                sign_up_params['SecretHash'] = secret_hash
            
            response = self.client.sign_up(**sign_up_params)
            
            result = {
                'user_sub': response.get('UserSub'),
                'user_confirmed': response.get('UserConfirmed', False),
                'code_delivery_details': response.get('CodeDeliveryDetails')
            }
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('register', duration_ms=duration_ms, email=email)
            logger.info(f"User registered successfully: {email}")
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self._log_error('register', e, email=email)
            
            if error_code == 'UsernameExistsException':
                logger.warning(f"Registration failed: User {email} already exists")
            elif error_code == 'InvalidPasswordException':
                logger.warning(f"Registration failed for {email}: Password does not meet requirements")
            else:
                logger.error(f"Registration failed for {email}: {error_code}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return None
    
    def verify_user(self, username: str, confirmation_code: str) -> bool:
        """
        Verify user registration with confirmation code
        
        Args:
            username: User's email/username
            confirmation_code: Verification code sent to user's email
            
        Returns:
            True if verification successful, False otherwise
        """
        try:
            self._log_operation('verify_user', username=username)
            
            # Add SECRET_HASH if client secret is configured
            confirm_params = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code
            }
            
            if self.client_secret:
                import hmac
                import hashlib
                import base64
                message = bytes(username + self.client_id, 'utf-8')
                secret = bytes(self.client_secret, 'utf-8')
                secret_hash = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest()).decode()
                confirm_params['SecretHash'] = secret_hash
            
            self.client.confirm_sign_up(**confirm_params)
            
            self._log_success('verify_user', username=username)
            logger.info(f"User verified successfully: {username}")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self._log_error('verify_user', e, username=username)
            logger.error(f"User verification failed for {username}: {error_code}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during user verification: {str(e)}")
            return False
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Cognito refresh token
            
        Returns:
            Dictionary with new tokens or None
        """
        try:
            self._log_operation('refresh_token')
            
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            if 'AuthenticationResult' in response:
                auth_result = response['AuthenticationResult']
                tokens = {
                    'access_token': auth_result.get('AccessToken'),
                    'id_token': auth_result.get('IdToken'),
                    'expires_in': auth_result.get('ExpiresIn'),
                    'token_type': auth_result.get('TokenType')
                }
                
                self._log_success('refresh_token')
                logger.info("Token refreshed successfully")
                
                return tokens
            else:
                logger.warning("Token refresh response missing AuthenticationResult")
                return None
                
        except ClientError as e:
            self._log_error('refresh_token', e)
            logger.error(f"Token refresh failed: {e.response['Error']['Code']}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            return None
    
    def logout(self, access_token: str) -> bool:
        """
        Logout user and revoke tokens
        
        Args:
            access_token: User's access token
            
        Returns:
            True if logout successful, False otherwise
        """
        try:
            self._log_operation('logout')
            
            self.client.global_sign_out(
                AccessToken=access_token
            )
            
            self._log_success('logout')
            logger.info("User logged out successfully")
            
            return True
            
        except ClientError as e:
            self._log_error('logout', e)
            logger.error(f"Logout failed: {e.response['Error']['Code']}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during logout: {str(e)}")
            return False
    
    def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate access token and get user information
        
        Args:
            access_token: User's access token
            
        Returns:
            Dictionary with user information or None if invalid
        """
        try:
            response = self.client.get_user(
                AccessToken=access_token
            )
            
            user_info = {
                'username': response.get('Username'),
                'attributes': {attr['Name']: attr['Value'] for attr in response.get('UserAttributes', [])}
            }
            
            return user_info
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                logger.warning("Token validation failed: Token expired or invalid")
            else:
                logger.error(f"Token validation failed: {error_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return None
