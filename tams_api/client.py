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
        timestamp = int(time.time())
        return hashlib.md5(str(timestamp).encode()).hexdigest()
    
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
        full_url = f"{self.api_endpoint}{url_path}"
        
        # Convert data to JSON string if it's a dict
        data_str = None
        if data is not None:
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = data
        
        # Generate signature and headers
        timestamp = int(time.time())
        headers = self.signature_generator.generate_signature(
            http_method=method,
            url_path=url_path,
            request_body=data_str,
            timestamp=timestamp
        )
        
        # Add API key to headers
        headers['X-API-Key'] = self.api_key
        
        # Debug log the request (masked for security)
        logger.debug(f"Making {method} request to {full_url}")
        logger.debug(f"Headers: {self._mask_headers(headers)}")
        if data_str:
            logger.debug(f"Request body: {data_str[:100]}{'...' if len(data_str) > 100 else ''}")
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == 'GET':
                    async with session.get(full_url, headers=headers) as response:
                        return await self._handle_response(response)
                elif method.upper() == 'POST':
                    async with session.post(full_url, headers=headers, data=data_str) as response:
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
            auth_parts = masked_headers['Authorization'].split(':')
            if len(auth_parts) >= 3:
                # Mask the signature part
                masked_headers['Authorization'] = f"{':'.join(auth_parts[:-1])}:***"
        if 'X-API-Key' in masked_headers:
            masked_headers['X-API-Key'] = '***'
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
            
            # Try to get the response body as text first
            body_text = await response.text()
            logger.debug(f"Response body: {body_text[:100]}{'...' if len(body_text) > 100 else ''}")
            
            # Try to parse as JSON
            try:
                response_json = json.loads(body_text)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {body_text}")
                raise Exception(f"Invalid API response (not JSON): Status {response.status}")
            
            # Check if the response indicates an error
            if response.status >= 400:
                error_message = response_json.get('message', 'Unknown error')
                error_code = response_json.get('code', 'UNKNOWN')
                logger.error(f"API error {response.status} ({error_code}): {error_message}")
                raise Exception(f"API error {response.status} ({error_code}): {error_message}")
            
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
            raise ValueError("Model ID is required")
        
        # Create the job payload
        payload = {
            "requestId": request_id,
            "stages": [
                {
                    "type": "INPUT_INITIALIZE",
                    "inputInitialize": {
                        "seed": "-1",  # Use random seed
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
                        "cfgScale": 7,
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
        return await self._make_request('POST', '/v1/jobs', data=payload)
    
    async def get_job_status(self, job_id):
        """
        Get the status of a job
        
        Args:
            job_id (str): The job ID
            
        Returns:
            dict: API response with job status information
        """
        logger.info(f"Checking status of job: {job_id}")
        return await self._make_request('GET', f'/v1/jobs/{job_id}')
    
    async def list_models(self, page=1, page_size=10, model_type="CHECKPOINT"):
        """
        List available models
        
        Args:
            page (int): Page number
            page_size (int): Number of items per page
            model_type (str): Type of model to list
            
        Returns:
            dict: API response with model information
        """
        logger.info(f"Listing models of type {model_type}, page {page}")
        return await self._make_request(
            'GET', 
            f'/v1/models?page={page}&pageSize={page_size}&modelType={model_type}'
        )
    
    async def get_model_details(self, model_id):
        """
        Get details about a specific model
        
        Args:
            model_id (str): The model ID
            
        Returns:
            dict: API response with model details
        """
        logger.info(f"Getting details for model: {model_id}")
        return await self._make_request('GET', f'/v1/models/{model_id}')
