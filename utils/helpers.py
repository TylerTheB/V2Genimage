#!/usr/bin/env python3
"""
Helper functions for the Tensor Art Telegram Bot.
"""
import time
import hashlib
import logging
import re
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

def validate_prompt(prompt):
    """
    Validate and clean a user prompt.
    
    Args:
        prompt (str): The user's prompt text
        
    Returns:
        tuple: (is_valid, cleaned_prompt, error_message)
    """
    # Check if prompt is empty
    if not prompt or prompt.strip() == "":
        return False, "", "Prompt cannot be empty. Please provide a description."
    
    # Trim whitespace
    cleaned_prompt = prompt.strip()
    
    # Check minimum length
    if len(cleaned_prompt) < 3:
        return False, cleaned_prompt, "Prompt is too short. Please provide a more detailed description."
    
    # Check maximum length (Tensor Art may have specific limits)
    if len(cleaned_prompt) > 1000:
        return False, cleaned_prompt, "Prompt is too long. Please keep it under 1000 characters."
    
    # Optional: Filter out potentially harmful content
    # This is a very basic check - consider using a more sophisticated approach
    harmful_patterns = [
        r'(?i)child.*porn',
        r'(?i)kill.*yourself',
        # Add more patterns as needed
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, cleaned_prompt):
            return False, "", "Your prompt contains inappropriate content. Please try a different prompt."
    
    return True, cleaned_prompt, ""

def process_image(image_data, max_size=None):
    """
    Process an image before sending it to the user.
    
    Args:
        image_data (bytes): Raw image data
        max_size (tuple, optional): Maximum (width, height) to resize to
        
    Returns:
        bytes: Processed image data
    """
    try:
        # Open image from bytes
        img = Image.open(BytesIO(image_data))
        
        # Resize if necessary
        if max_size and (img.width > max_size[0] or img.height > max_size[1]):
            img.thumbnail(max_size, Image.LANCZOS)
        
        # Convert to output format
        output = BytesIO()
        img.save(output, format="JPEG", quality=95)
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return image_data  # Return original if processing fails

def generate_request_id():
    """
    Generate a unique request ID based on the current timestamp.
    
    Returns:
        str: Unique request ID
    """
    timestamp = int(time.time() * 1000)  # Millisecond precision
    random_data = f"{timestamp}{hash(time.time())}"
    return hashlib.md5(random_data.encode()).hexdigest()

def parse_model_list(models_response):
    """
    Parse the model list response from Tensor Art API.
    
    Args:
        models_response (dict): API response containing models
        
    Returns:
        list: List of model dictionaries with key information
    """
    parsed_models = []
    
    try:
        if not models_response or 'models' not in models_response:
            return parsed_models
            
        models = models_response.get('models', [])
        
        for model in models:
            parsed_models.append({
                'id': model.get('id'),
                'name': model.get('name'),
                'type': model.get('type'),
                'description': model.get('description'),
                'tags': model.get('tags', [])
            })
            
        return parsed_models
    except Exception as e:
        logger.error(f"Error parsing model list: {str(e)}")
        return []

def format_error_message(error):
    """
    Format an error message for user display.
    
    Args:
        error (Exception or str): The error
        
    Returns:
        str: Formatted error message
    """
    if isinstance(error, Exception):
        error_str = str(error)
    else:
        error_str = error
        
    # Remove sensitive information if present
    error_str = re.sub(r'app_id=[\w-]+', 'app_id=***', error_str)
    error_str = re.sub(r'api_key=[\w-]+', 'api_key=***', error_str)
    
    # Simplify complex error messages
    if 'Unauthorized' in error_str or '401' in error_str:
        return "Authentication error. Please contact the bot administrator."
    
    if 'Timeout' in error_str:
        return "The server took too long to respond. Please try again later."
    
    # Keep the message user-friendly
    if len(error_str) > 100:
        return f"An error occurred: {error_str[:100]}..."
    
    return f"An error occurred: {error_str}"
