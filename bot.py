#!/usr/bin/env python3
import os
import logging
import asyncio
import time
import hashlib
import base64
from telethon.sync import TelegramClient, events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights
import aiohttp
from io import BytesIO
from config import Config
from tams_api.client import TensorArtClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration from environment variables
config = Config()

# Initialize Telegram client
bot = TelegramClient(
    'tams_image_bot',
    config.TELEGRAM_API_ID,
    config.TELEGRAM_API_HASH
)

# Initialize Tensor Art API client
tams_client = TensorArtClient(
    app_id=config.TAMS_APP_ID,
    api_key=config.TAMS_API_KEY,
    private_key_path=config.TAMS_PRIVATE_KEY_PATH,
    api_endpoint=config.TAMS_API_ENDPOINT
)

async def download_image(url):
    """Download an image from a URL and return it as bytes"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                logger.error(f"Failed to download image: {response.status}")
                return None

@bot.on(events.NewMessage(pattern=r'/imagine .*'))
async def handle_imagine_command(event):
    """Handle /imagine command to generate an image using Tensor Art API"""
    try:
        # Extract the prompt from the message
        prompt = event.message.text.replace('/imagine', '', 1).strip()
        
        if not prompt:
            await event.respond("Please provide a prompt after the /imagine command.")
            return
        
        # Send a waiting message
        waiting_msg = await event.respond("🎨 Generating your image... This may take a moment.")
        
        # Generate a unique request ID
        timestamp = int(time.time())
        request_id = hashlib.md5(str(timestamp).encode()).hexdigest()
        
        # Generate the image using Tensor Art API
        try:
            # Choose a model - using a popular SD model from Tensor Art
            model_id = "600423083519508503"  # Example model ID, should be configured
            
            # Request image generation
            job_result = await tams_client.create_text_to_image_job(
                request_id=request_id,
                prompt=prompt,
                model_id=model_id,
                width=768,
                height=768,
                steps=25,
                sampler="DPM++ 2M Karras"
            )
            
            # Get the job ID from the response
            job_id = job_result.get('jobId')
            if not job_id:
                raise Exception("Failed to get job ID from API response")
            
            # Poll for job completion
            image_url = None
            max_attempts = 30
            for _ in range(max_attempts):
                job_status = await tams_client.get_job_status(job_id)
                
                status = job_status.get('status')
                if status == 'COMPLETED':
                    # Get the image URL from the response
                    resources = job_status.get('resources', [])
                    if resources and len(resources) > 0:
                        image_url = resources[0].get('url')
                        break
                
                elif status in ['FAILED', 'CANCELED']:
                    raise Exception(f"Job {status}: {job_status.get('message', 'No error message')}")
                
                # Wait before polling again
                await asyncio.sleep(2)
            
            if not image_url:
                raise Exception("Failed to get image URL after job completion")
            
            # Download the generated image
            image_data = await download_image(image_url)
            if not image_data:
                raise Exception("Failed to download the generated image")
            
            # Send the image to the user
            await bot.send_file(
                event.chat_id,
                BytesIO(image_data),
                caption=f"Generated image for: {prompt}"
            )
            
            # Delete the waiting message
            await waiting_msg.delete()
            
        except Exception as api_error:
            logger.error(f"API Error: {str(api_error)}")
            await waiting_msg.edit(f"❌ Failed to generate image: {str(api_error)}")
    
    except Exception as e:
        logger.error(f"Error handling /imagine command: {str(e)}")
        await event.respond(f"❌ An error occurred: {str(e)}")

@bot.on(events.NewMessage(pattern='/start'))
async def handle_start_command(event):
    """Handle /start command to introduce the bot"""
    await event.respond(
        "🎨 Welcome to the Tensor Art Image Generator Bot! 🎨\n\n"
        "I can generate images based on your text descriptions using AI.\n\n"
        "To generate an image, use the command:\n"
        "/imagine <your description>\n\n"
        "For example: /imagine a horse on cloud"
    )

@bot.on(events.NewMessage(pattern='/help'))
async def handle_help_command(event):
    """Handle /help command to show usage instructions"""
    await event.respond(
        "🔍 **Help Guide** 🔍\n\n"
        "Use the following commands:\n\n"
        "• `/start` - Start the bot and get a welcome message\n"
        "• `/imagine <prompt>` - Generate an image based on your prompt\n"
        "• `/help` - Show this help message\n\n"
        "**Examples:**\n"
        "• `/imagine a beautiful sunset over mountains`\n"
        "• `/imagine a cat wearing a hat in cyberpunk style`\n\n"
        "The image generation usually takes 15-30 seconds depending on complexity."
    )

async def main():
    """Main function to start the bot"""
    # Start the client
    await bot.start(bot_token=config.TELEGRAM_BOT_TOKEN)
    
    # Run the client until disconnected
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
