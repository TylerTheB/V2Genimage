#!/usr/bin/env python3
import asyncio
import json
import logging
import time
import hashlib
from .auth import SignatureGenerator
import aiohttp

logger = logging.getLogger(__name__)

class TensorArtClient:
    """Client for interacting with the Tensor Art API"""
    
    def __init__(self, app_id, api_key, private_key_path=None, private_key_data=None, api_endpoint=None):
        """
        Initialize the Tensor Art API client
        
        Args:
            app_id (str): Tensor Art application ID
            api_key (str): Tensor Art API key
            private_key_path (str, optional): Path to the private key file
            private_key_data (bytes, optional): The private key data as bytes
            api_endpoint (str, optional): Base URL for the API
        """
        self.app_id = app_id
        self.api_key = api_key
        self.api_endpoint = api_endpoint or "https://ap-east-1.tensorart.cloud"
        
        # Initialize the signature generator
        self.signature_generator = SignatureGenerator(
            app_id=app_id,
            private_key_path=private_key_path,
            private_key_data=private_key_data
        )
    
    def _generate_request_id(self):
        """Generate a unique request ID based on the current timestamp"""
        timestamp = str(int(time.time()))
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    async def _make_request(self, method, url_path, data=None):
        """
        Make a request to the Tensor Art API
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            url_path (str): API endpoint path
            data (dict, optional): Request body for POST requests
            
        Returns:
            dict: API response
        """
        # Ensure the path starts with /
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        
        full_url = f"{self.api_endpoint}{url_path}"
        
        # Convert data to JSON string if it's a dict
        body_data = None
        if data is not None:
            # Important: Create a consistent JSON representation
            # Sort keys to ensure consistent ordering
            body_data = json.dumps(data, separators=(',', ':'), sort_keys=True)
        
        # Generate signature and headers
        # We need to pass the exact JSON string that will be sent
        headers = self.signature_generator.generate_signature(
            http_method=method,
            url_path=url_path,
            request_body=body_data
        )
        
        # Debug log the request
        logger.debug(f"Making {method} request to {full_url}")
        logger.debug(f"Headers: {json.dumps(self._mask_headers(headers), indent=2)}")
        if body_data:
            logger.debug(f"Request body: {body_data}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method.upper() == 'GET':
                    async with session.get(full_url, headers=headers) as response:
                        return await self._handle_response(response)
                elif method.upper() == 'POST':
                    async with session.post(
                        full_url, 
                        headers=headers, 
                        data=body_data  # Send as raw JSON string
                    ) as response:
                        return await self._handle_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"API request failed: {str(e)}")
    
    def _mask_headers(self, headers):
        """Mask sensitive information in headers for logging"""
        masked_headers = headers.copy()
        if 'Authorization' in masked_headers:
            # Parse the authorization header and mask the signature
            auth = masked_headers['Authorization']
            if 'signature=' in auth:
                parts = auth.split(',')
                for i, part in enumerate(parts):
                    if part.strip().startswith('signature='):
                        # Show only first 10 chars of signature
                        sig_value = part.split('=', 1)[1]
                        parts[i] = f'signature={sig_value[:10]}...'
                masked_headers['Authorization'] = ','.join(parts)
        return masked_headers
    
    async def _handle_response(self, response):
        """
        Handle the API response
        
        Args:
            response (aiohttp.ClientResponse): The API response
            
        Returns:
            dict: Parsed response JSON
        """
        try:
            # Log the response status and headers
            logger.debug(f"Response status: {response.status}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Read the response body
            body_text = await response.text()
            
            # For debugging 401 errors, log more of the response
            if response.status == 401:
                logger.error(f"401 Response body: {body_text}")
            else:
                logger.debug(f"Response body: {body_text[:500]}{'...' if len(body_text) > 500 else ''}")
            
            # Try to parse as JSON
            try:
                response_json = json.loads(body_text)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {body_text}")
                raise Exception(f"Invalid API response (not JSON): Status {response.status}, Body: {body_text}")
            
            # Check response status
            if response.status >= 400:
                error_code = response_json.get('code', 'UNKNOWN')
                error_message = response_json.get('message', response_json.get('msg', 'Unknown error'))
                tips = response_json.get('tips', '')
                
                logger.error(f"API error {response.status} ({error_code}): {error_message}")
                if tips:
                    logger.error(f"Tips from server: {tips}")
                logger.error(f"Full error response: {json.dumps(response_json, indent=2)}")
                
                # Include tips in the error message if available
                error_msg = f"API error {response.status} ({error_code}): {error_message}"
                if tips:
                    error_msg += f"\nServer tips: {tips}"
                raise Exception(error_msg)
            
            # Check for errors in successful responses
            if 'code' in response_json and response_json['code'] != 0:
                error_code = response_json.get('code', 'UNKNOWN')
                error_message = response_json.get('message', response_json.get('msg', 'Unknown error'))
                logger.error(f"API error ({error_code}): {error_message}")
                raise Exception(f"API error ({error_code}): {error_message}")
            
            return response_json
            
        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            raise
    
    async def create_text_to_image_job(self, request_id=None, prompt="", model_id=None, 
                                       width=512, height=512, steps=25, sampler="DPM++ 2M Karras",
                                       negative_prompt=""):
        """
        Create a text-to-image job
        """
        if not request_id:
            request_id = self._generate_request_id()
        
        if not model_id:
            model_id = "600423083519508503"  # Default model
        
        # Create the job payload in the exact format TAMS expects
        payload = {
            "requestId": request_id,
            "stages": [
                {
                    "type": "INPUT_INITIALIZE",
                    "inputInitialize": {
                        "seed": -1,
                        "count": 1
                    }
                },
                {
                    "type": "DIFFUSION",
                    "diffusion": {
                        "width": width,
                        "height": height,
                        "prompts": [{"text": prompt}],
                        "negativePrompts": [],  # Empty array as shown in the error message
                        "sdModel": model_id,
                        "sdVae": "Automatic",
                        "sampler": sampler,
                        "steps": steps,
                        "cfgScale": 7.0,
                        "clipSkip": 2
                    }
                }
            ]
        }
        
        # Log the job creation details
        logger.info(f"Creating text-to-image job with request ID: {request_id}")
        logger.info(f"Using model: {model_id}")
        logger.info(f"Prompt: {prompt}")
        
        # Make the API request
        response = await self._make_request('POST', '/v1/jobs', data=payload)
        return response
    
    async def get_job_status(self, job_id):
        """
        Get the status of a job
        """
        logger.info(f"Checking status of job: {job_id}")
        response = await self._make_request('GET', f'/v1/jobs/{job_id}')
        return response
