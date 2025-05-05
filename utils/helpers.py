#!/usr/bin/env python3
import hashlib
import time
import logging
import json
import io
import os
from datetime import datetime
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

def generate_request_id() -> str:
    """
    Generate a unique request ID based on the current timestamp
    
    Returns:
        str: MD5 hash of the current timestamp
    """
    timestamp = int(time.time())
    return hashlib.md5(str(timestamp).encode()).hexdigest()

def format_prompt(prompt: str) -> str:
    """
    Format a user-provided prompt for better results
    
    Args:
        prompt (str): Raw user prompt
        
    Returns:
        str: Formatted prompt
    """
    # Remove leading/trailing whitespace
    formatted = prompt.strip()
    
    # Add quality enhancers if they're not already in the prompt
    quality_enhancers = ["high quality", "detailed", "professional", "4k"]
    
    # Check if any quality enhancer is already in the prompt
    has_quality_term = any(term in formatted.lower() for term in quality_enhancers)
    
    # If no quality term is present, add "high quality" to the prompt
    if not has_quality_term:
        formatted += ", high quality"
    
    return formatted

def resize_image(image_data: bytes, max_width: int = 1024, max_height: int = 1024) -> bytes:
    """
    Resize an image to fit within maximum dimensions while preserving aspect ratio
    
    Args:
        image_data (bytes): Image data as bytes
        max_width (int): Maximum width
        max_height (int): Maximum height
        
    Returns:
        bytes: Resized image data
    """
    try:
        # Create an image object from the bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Get original dimensions
        width, height = image.size
        
        # Check if resizing is needed
        if width <= max_width and height <= max_height:
            return image_data
        
        # Calculate new dimensions while preserving aspect ratio
        aspect_ratio = width / height
        
        if width > height:
            new_width = min(width, max_width)
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = min(height, max_height)
            new_width = int(new_height * aspect_ratio)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert back to bytes
        buffer = io.BytesIO()
        resized_image.save(buffer, format=image.format or 'PNG')
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}")
        # Return original image if resizing fails
        return image_data

def get_popular_models() -> List[Dict[str, str]]:
    """
    Get a list of popular models from Tensor Art
    
    Returns:
        List[Dict[str, str]]: List of popular models with ID and name
    """
    # This is a static list of popular models
    # In a real implementation, you might fetch this from the API
    return [
        {"id": "600423083519508503", "name": "Dreamshaper 8", "type": "CHECKPOINT"},
        {"id": "619225630271212879", "name": "SDXL 1.0", "type": "CHECKPOINT"},
        {"id": "664552050473852151", "name": "Realistic Vision 5.1", "type": "CHECKPOINT"},
        {"id": "681693017352010007", "name": "Dreamshaper XL", "type": "CHECKPOINT"},
        {"id": "665542932812005686", "name": "FLUX", "type": "CHECKPOINT"}
    ]

def process_image_bytes(image_data: bytes, output_format: str = 'PNG') -> Tuple[bytes, str]:
    """
    Process image bytes to ensure correct format and optimize for Telegram
    
    Args:
        image_data (bytes): Raw image data
        output_format (str): Desired output format (PNG, JPEG, etc.)
        
    Returns:
        Tuple[bytes, str]: Processed image data and mimetype
    """
    try:
        # Open the image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed (e.g., if it's RGBA)
        if image.mode in ('RGBA', 'LA') and output_format.upper() == 'JPEG':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
            image = background
        
        # Convert to desired format
        buffer = io.BytesIO()
        image.save(buffer, format=output_format)
        processed_data = buffer.getvalue()
        
        # Determine mimetype
        mimetype = f"image/{output_format.lower()}"
        
        return processed_data, mimetype
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        # Return original data if processing fails
        return image_data, "image/png"

def log_request(request_id: str, endpoint: str, payload: Dict[str, Any]) -> None:
    """
    Log an API request for debugging purposes
    
    Args:
        request_id (str): The request ID
        endpoint (str): The API endpoint
        payload (Dict[str, Any]): The request payload
    """
    try:
        # Create a copy of the payload to avoid modifying the original
        payload_copy = json.loads(json.dumps(payload))
        
        # Truncate prompts if they're too long
        if "stages" in payload_copy:
            for stage in payload_copy.get("stages", []):
                if "diffusion" in stage:
                    diffusion = stage["diffusion"]
                    if "prompts" in diffusion:
                        for i, prompt in enumerate(diffusion["prompts"]):
                            if "text" in prompt and len(prompt["text"]) > 50:
                                prompt["text"] = prompt["text"][:50] + "..."
        
        logger.info(f"API Request {request_id} to {endpoint}: {json.dumps(payload_copy)}")
    except Exception as e:
        logger.error(f"Error logging request: {str(e)}")

def log_response(request_id: str, endpoint: str, response: Dict[str, Any]) -> None:
    """
    Log an API response for debugging purposes
    
    Args:
        request_id (str): The request ID
        endpoint (str): The API endpoint
        response (Dict[str, Any]): The API response
    """
    try:
        # Create a copy of the response to avoid modifying the original
        response_copy = json.loads(json.dumps(response))
        
        # Remove large fields or sensitive data
        if "resources" in response_copy:
            for resource in response_copy.get("resources", []):
                if "data" in resource:
                    resource["data"] = "<binary data>"
        
        logger.info(f"API Response {request_id} from {endpoint}: {json.dumps(response_copy)}")
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")

def format_error(error: Exception, public: bool = True) -> str:
    """
    Format an error message for display to the user or for logging
    
    Args:
        error (Exception): The error
        public (bool): Whether the message is for public display
        
    Returns:
        str: Formatted error message
    """
    error_str = str(error)
    
    if public:
        # For public-facing errors, provide a user-friendly message
        if "unauthorized" in error_str.lower() or "authentication" in error_str.lower():
            return "❌ Authentication error. Please check API credentials."
        elif "timed out" in error_str.lower() or "timeout" in error_str.lower():
            return "❌ The request timed out. Please try again later."
        elif "rate limit" in error_str.lower():
            return "❌ Rate limit exceeded. Please try again in a few minutes."
        else:
            # Generic error message for other errors
            return f"❌ An error occurred: {error_str}"
    else:
        # For logging, include more details
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] Error: {error.__class__.__name__}: {error_str}"
