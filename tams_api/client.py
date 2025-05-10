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
            if isinstance(data, dict):
                body_data = json.dumps(data, separators=(',', ':'), sort_keys=True)
            else:
                body_data = data
        
        # Generate signature and headers
        headers = self.signature_generator.generate_signature(
            http_method=method,
            url_path=url_path,
            request_body=body_data
        )
        
        # Add additional headers
        headers['x-tams-app-id'] = self.app_id
        headers['x-tams-api-key'] = self.api_key
        
        # Debug log the request (masked for security)
        logger.debug(f"Making {method} request to {full_url}")
        logger.debug(f"Headers: {self._mask_headers(headers)}")
        if body_data:
            logger.debug(f"Request body: {body_data[:100]}{'...' if len(body_data) > 100 else ''}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method.upper() == 'GET':
                    async with session.get(full_url, headers=headers) as response:
                        return await self._handle_response(response)
                elif method.upper() == 'POST':
                    async with session.post(
                        full_url, 
                        headers=headers, 
                        data=body_data,
                        ssl=False  # Disable SSL verification for debugging
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
            masked_headers['Authorization'] = '***'
        if 'x-tams-api-key' in masked_headers:
            masked_headers['x-tams-api-key'] = '***'
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
            # Log the response status
            logger.debug(f"Response status: {response.status}")
            
            # Read the response body
            body_text = await response.text()
            logger.debug(f"Response body: {body_text[:200]}{'...' if len(body_text) > 200 else ''}")
            
            # Try to parse as JSON
            try:
                response_json = json.loads(body_text)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {body_text}")
                raise Exception(f"Invalid API response (not JSON): Status {response.status}, Body: {body_text}")
            
            # Check if the response indicates an error
            if response.status >= 400:
                error_code = response_json.get('code', 'UNKNOWN')
                error_message = response_json.get('message', response_json.get('msg', 'Unknown error'))
                logger.error(f"API error {response.status} ({error_code}): {error_message}")
                logger.error(f"Full response: {response_json}")
                raise Exception(f"API error {response.status} ({error_code}): {error_message}")
            
            # For successful responses, check if there's still an error in the body
            if 'code' in response_json and response_json['code'] != 0:
                error_code = response_json.get('code', 'UNKNOWN')
                error_message = response_json.get('message', response_json.get('msg', 'Unknown error'))
                logger.error(f"API error ({error_code}): {error_message}")
                raise Exception(f"API error ({error_code}): {error_message}")
            
            return response_json
            
        except aiohttp.ContentTypeError:
            # If the response is not valid JSON
            text = await response.text()
            logger.error(f"Invalid JSON response: {text}")
            raise Exception(f"Invalid API response (not JSON): Status {response.status}")
    
    async def create_text_to_image_job(self, request_id=None, prompt="", model_id=None, 
                                       width=512, height=512, steps=25, sampler="DPM++ 2M Karras",
                                       negative_prompt=""):
        """
        Create a text-to-image job
        
        Args:
            request_id (str, optional): Unique request ID (generated if not provided)
            prompt (str): Text prompt for image generation
            model_id (str): ID of the model to use
            width (int): Width of the generated image
            height (int): Height of the generated image
            steps (int): Number of denoising steps
            sampler (str): Sampling method
            negative_prompt (str): Negative prompt for image generation
            
        Returns:
            dict: API response with job information
        """
        if not request_id:
            request_id = self._generate_request_id()
        
        if not model_id:
            # Use a default model ID if none provided
            model_id = "600423083519508503"
        
        # Create the job payload using simpler format
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
                        "negativePrompts": [{"text": negative_prompt}] if negative_prompt else [],
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
        
        Args:
            job_id (str): The job ID
            
        Returns:
            dict: API response with job status information
        """
        logger.info(f"Checking status of job: {job_id}")
        response = await self._make_request('GET', f'/v1/jobs/{job_id}')
        return response
