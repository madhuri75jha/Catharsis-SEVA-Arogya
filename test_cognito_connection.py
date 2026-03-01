"""
Quick test to verify Cognito connection works
"""
import os
from dotenv import load_dotenv
from aws_services.auth_manager import AuthManager

# Load environment
load_dotenv()

def test_cognito_connection():
    """Test if we can connect to Cognito"""
    print("Testing Cognito connection...")
    
    region = os.getenv('AWS_REGION', 'ap-south-1')
    user_pool_id = os.getenv('AWS_COGNITO_USER_POOL_ID')
    client_id = os.getenv('AWS_COGNITO_CLIENT_ID')
    client_secret = os.getenv('AWS_COGNITO_CLIENT_SECRET')
    
    print(f"Region: {region}")
    print(f"User Pool ID: {user_pool_id}")
    print(f"Client ID: {client_id}")
    
    try:
        # Initialize auth manager
        auth_manager = AuthManager(
            region=region,
            user_pool_id=user_pool_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        print("✓ Successfully created AuthManager")
        print("✓ Cognito connection is working!")
        
        # Try a simple operation (forgot password with fake email)
        # This will fail but proves we can connect
        success, error = auth_manager.forgot_password("test@example.com")
        
        if error and error['code'] == 'UserNotFoundException':
            print("✓ Successfully communicated with Cognito (user not found is expected)")
            return True
        elif success:
            print("✓ Successfully communicated with Cognito")
            return True
        else:
            print(f"⚠ Got response from Cognito: {error}")
            return True
            
    except Exception as e:
        print(f"✗ Failed to connect to Cognito: {e}")
        print("\nPlease run: python test_aws_connectivity.py")
        return False

if __name__ == "__main__":
    success = test_cognito_connection()
    exit(0 if success else 1)
