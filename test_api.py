#!/usr/bin/env python3
import os
import asyncio
import logging
from dotenv import load_dotenv
from tams_api.client import TensorArtClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API credentials from environment variables
app_id = os.getenv('TAMS_APP_ID')
api_key = os.getenv('TAMS_API_KEY')
private_key_path = os.getenv('TAMS_PRIVATE_KEY_PATH')
private_key_base64 = os.getenv('TAMS_PRIVATE_KEY_BASE64')
api_endpoint = os.getenv('TAMS_API_ENDPOINT')

# Check if we have necessary credentials
if not app_id or not api_key:
    raise ValueError("TAMS_APP_ID and TAMS_API_KEY environment variables are required")

if not private_key_path and not private_key_base64:
    raise ValueError("Either TAMS_PRIVATE_KEY_PATH or TAMS_PRIVATE_KEY_BASE64 is required")

# If private key is provided as base64, save it to a temporary file
if private_key_base64 and not private_key_path:
    import base64
    
    # Decode the base64 string
    private_key_data = base64.b64decode(private_key_base64)
    
    # Create a temporary file to store the private key
    temp_file_path = "temp_private_key.pem"
    with open(temp_file_path, 'wb') as f:
        f.write(private_key_data)
    
    private_key_path = temp_file_path
    logger.info(f"Saved base64 private key to temporary file: {temp_file_path}")

# Initialize the client
client = TensorArtClient(
    app_id=app_id,
    api_key=api_key,
    private_key_path=private_key_path,
    api_endpoint=api_endpoint
)

async def test_list_models():
    """Test listing models from the API"""
    logger.info("Testing list_models API...")
    try:
        models = await client.list_models(page=1, page_size=5)
        logger.info(f"Successfully listed models. Found {len(models.get('models', []))} models")
        return True
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return False

async def test_create_job():
    """Test creating a text-to-image job"""
    logger.info("Testing create_text_to_image_job API...")
    try:
        # Use a simple test prompt
        prompt = "A beautiful sunset over mountains"
        model_id = "600423083519508503"  # Example model ID (Dreamshaper 8)
        
        job_result = await client.create_text_to_image_job(
            prompt=prompt,
            model_id=model_id,
            width=512,
            height=512,
            steps=20
        )
        
        job_id = job_result.get('jobId')
        if job_id:
            logger.info(f"Successfully created job with ID: {job_id}")
            
            # Check job status
            logger.info("Checking job status...")
            status = await client.get_job_status(job_id)
            logger.info(f"Job status: {status.get('status')}")
            
            return True
        else:
            logger.error("No job ID returned from API")
            return False
            
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return False

async def main():
    """Run the tests"""
    logger.info("Starting API tests...")
    
    # Test listing models
    models_success = await test_list_models()
    
    # Only test job creation if listing models was successful
    if models_success:
        job_success = await test_create_job()
        
        if job_success:
            logger.info("All tests passed successfully!")
        else:
            logger.error("Job creation test failed")
    else:
        logger.error("Model listing test failed, skipping job creation test")

if __name__ == "__main__":
    asyncio.run(main())
