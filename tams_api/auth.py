#!/usr/bin/env python3
import base64
import json
import time
import logging
import hashlib
import uuid
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
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
            self.private_key = serialization.load_pem_private_key(
                private_key_data,
                password=None,
                backend=default_backend()
            )
            logger.debug("Successfully loaded private key")
        except Exception as e:
            logger.error(f"Failed to load private key: {str(e)}")
            raise ValueError(f"Failed to load private key: {str(e)}")
    
    def generate_signature(self, http_method, url_path, request_body=None, timestamp=None):
        """
        Generate a signature for Tensor Art API request
        
        Args:
            http_method (str): HTTP method (GET, POST, etc.)
            url_path (str): API endpoint path
            request_body (str, optional): Request body as string
            timestamp (int, optional): Timestamp to use for signature (default: current time)
            
        Returns:
            dict: Headers with signature information
        """
        # Use current timestamp if not provided
        if timestamp is None:
            timestamp = int(time.time())
        
        # Generate a unique nonce string for this request
        nonce_str = str(uuid.uuid4())
        
        # Create the data to sign
        data_to_sign = self._create_data_to_sign(
            http_method, url_path, request_body, 
            self.app_id, nonce_str, timestamp
        )
        
        # Sign the data
        signature = self._sign_data(data_to_sign)
        
        # Create authorization header - TAMS specific format
        auth_header = f"TAMS-SHA256-RSA app_id={self.app_id},nonce_str={nonce_str},timestamp={timestamp},signature={signature}"
        
        return {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
    
    def _create_data_to_sign(self, http_method, url_path, request_body, app_id, nonce_str, timestamp):
        """Create the string to be signed according to TAMS spec"""
        # Components of the signature
        components = []
        
        # Add HTTP method
        components.append(http_method.upper())
        
        # Add URL path
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        components.append(url_path)
        
        # Add app_id
        components.append(app_id)
        
        # Add nonce_str
        components.append(nonce_str)
        
        # Add timestamp
        components.append(str(timestamp))
        
        # Add request body if present
        if request_body:
            components.append(request_body)
        
        # Join all components with newlines
        string_to_sign = '\n'.join(components)
        
        logger.debug(f"String to sign: {repr(string_to_sign)}")
        
        return string_to_sign.encode('utf-8')
    
    def _sign_data(self, data):
        """Sign the data with the private key using RSA SHA-256"""
        try:
            # Sign the data using RSA with SHA-256
            signature = self.private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Return base64 encoded signature
            base64_signature = base64.b64encode(signature).decode('utf-8')
            logger.debug(f"Generated signature (first 20 chars): {base64_signature[:20]}...")
            return base64_signature
        except Exception as e:
            logger.error(f"Failed to sign data: {str(e)}")
            raise ValueError(f"Failed to sign data: {str(e)}")
