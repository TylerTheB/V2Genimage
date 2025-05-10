#!/usr/bin/env python3
import base64
import json
import time
import logging
import hashlib
import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class SignatureGenerator:
    """Handles authentication and signature generation for Tensor Art API"""
    
    def __init__(self, app_id, private_key_path=None, private_key_data=None):
        """
        Initialize the signature generator with application ID and private key
        
        Args:
            app_id (str): The Tensor Art application ID
            private_key_path (str, optional): Path to the private key file (PEM format)
            private_key_data (bytes, optional): The private key data as bytes
        """
        self.app_id = app_id
        
        # Load the private key
        if private_key_path:
            self._load_private_key_from_file(private_key_path)
        elif private_key_data:
            self._load_private_key_from_data(private_key_data)
        else:
            raise ValueError("Either private_key_path or private_key_data must be provided")
    
    def _load_private_key_from_file(self, private_key_path):
        """Load private key from a file"""
        try:
            with open(private_key_path, 'rb') as key_file:
                self._load_private_key_from_data(key_file.read())
        except Exception as e:
            logger.error(f"Failed to load private key from file: {str(e)}")
            raise ValueError(f"Failed to load private key from file: {str(e)}")
    
    def _load_private_key_from_data(self, private_key_data):
        """Load private key from bytes data"""
        try:
            # First try PKCS#1 format
            self.private_key = serialization.load_pem_private_key(
                private_key_data,
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            # Try PKCS#8 format if the default PKCS#1 fails
            try:
                self.private_key = serialization.load_der_private_key(
                    private_key_data,
                    password=None,
                    backend=default_backend()
                )
            except Exception as nested_e:
                logger.error(f"Failed to load private key: {str(e)}, {str(nested_e)}")
                raise ValueError(f"Failed to load private key: {str(e)}, {str(nested_e)}")
    
    def generate_signature(self, http_method, url_path, request_body=None, timestamp=None):
        """
        Generate a signature for Tensor Art API request
        
        Args:
            http_method (str): HTTP method (GET, POST, etc.)
            url_path (str): API endpoint path
            request_body (dict, optional): Request body for POST/PUT requests
            timestamp (int, optional): Timestamp to use for signature (default: current time)
            
        Returns:
            dict: Headers with signature information
        """
        # Use current timestamp if not provided
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create the data to sign
        data_to_sign = self._create_data_to_sign(http_method, url_path, request_body, timestamp)
        
        # Sign the data
        signature = self._sign_data(data_to_sign)
        
        # Return headers with signature
        # The correct format is "Sign {app_id}:{timestamp}:{signature}"
        return {
            'Authorization': f'Sign {self.app_id}:{timestamp}:{signature}',
            'Content-Type': 'application/json'
        }
    
    def _create_data_to_sign(self, http_method, url_path, request_body, timestamp):
        """Create the string to be signed"""
        http_method = http_method.upper()
        
        # Handle request body
        content_md5 = ''
        if request_body is not None:
            if isinstance(request_body, dict):
                request_body_str = json.dumps(request_body, separators=(',', ':'))
            else:
                request_body_str = request_body
                
            content_md5 = hashlib.md5(request_body_str.encode('utf-8')).hexdigest()
        
        # Format the string to sign with line breaks between each component
        # String should be: method + '\n' + path + '\n' + timestamp + '\n' + md5
        string_to_sign = f"{http_method}\n{url_path}\n{timestamp}\n{content_md5}"
        return string_to_sign.encode('utf-8')
    
    def _sign_data(self, data):
        """Sign the data with the private key"""
        try:
            # Sign the data
            signature = self.private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Return base64 encoded signature
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to sign data: {str(e)}")
            raise ValueError(f"Failed to sign data: {str(e)}")
