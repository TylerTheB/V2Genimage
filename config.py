#!/usr/bin/env python3
import os
import base64
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration class for the Telegram bot and Tensor Art API"""
    
    def __init__(self):
        # Telegram Bot Credentials
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
        self.TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
        
        # Tensor Art API Credentials
        self.TAMS_APP_ID = os.getenv('TAMS_APP_ID', 'a_AYYMFy4')  # Default from prompt
        self.TAMS_API_KEY = os.getenv('TAMS_API_KEY', 'f2fa8b1cb7884975807f4cafa0f558c4')  # Default from prompt
        self.TAMS_API_ENDPOINT = os.getenv('TAMS_API_ENDPOINT', 'https://ap-east-1.tensorart.cloud')  # Default from prompt
        
        # Private key handling
        self.TAMS_PRIVATE_KEY_PATH = os.getenv('TAMS_PRIVATE_KEY_PATH')
        self.TAMS_PRIVATE_KEY_BASE64 = os.getenv('TAMS_PRIVATE_KEY_BASE64')
        
        # Validate required configuration
        self._validate_config()
        
        # If private key is provided as base64, save it to a temporary file
        if self.TAMS_PRIVATE_KEY_BASE64 and not self.TAMS_PRIVATE_KEY_PATH:
            self._save_private_key_from_base64()
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        missing_vars = []
        
        # Check Telegram credentials
        if not self.TELEGRAM_BOT_TOKEN:
            missing_vars.append('TELEGRAM_BOT_TOKEN')
        if not self.TELEGRAM_API_ID:
            missing_vars.append('TELEGRAM_API_ID')
        if not self.TELEGRAM_API_HASH:
            missing_vars.append('TELEGRAM_API_HASH')
        
        # Check Tensor Art credentials
        if not self.TAMS_APP_ID:
            missing_vars.append('TAMS_APP_ID')
        if not self.TAMS_API_KEY:
            missing_vars.append('TAMS_API_KEY')
        
        # Check private key (either file path or base64)
        if not self.TAMS_PRIVATE_KEY_PATH and not self.TAMS_PRIVATE_KEY_BASE64:
            missing_vars.append('TAMS_PRIVATE_KEY_PATH or TAMS_PRIVATE_KEY_BASE64')
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _save_private_key_from_base64(self):
        """Save base64 encoded private key to a temporary file"""
        try:
            # Decode the base64 string
            private_key_data = base64.b64decode(self.TAMS_PRIVATE_KEY_BASE64)
            
            # Create a temporary file to store the private key
            temp_file_path = "temp_private_key.pem"
            with open(temp_file_path, 'wb') as f:
                f.write(private_key_data)
            
            # Set the path to the private key file
            self.TAMS_PRIVATE_KEY_PATH = temp_file_path
            
            print(f"Private key saved to temporary file: {temp_file_path}")
        except Exception as e:
            raise ValueError(f"Failed to decode and save private key: {str(e)}")
