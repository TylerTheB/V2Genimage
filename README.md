# Creating a Telegram Bot with Tensor Art API Integration

This document outlines the steps to create a Telegram bot that generates images using the Tensor Art (TAMS) API when a user types `/imagine <prompt>`.

## Prerequisites

1. **Telegram Bot Token**: Create a bot through BotFather and get your bot token
2. **Tensor Art Account and API Key**: 
   - Sign up at [Tensor Art](https://tams.tensor.art/)
   - Create an application to get App ID and API Key
   - Generate RSA key pair for API authentication
   - Upload public key to TAMS platform
   - Store private key securely

## Understanding the API Flow

The Tensor Art API requires the following steps to generate an image:

1. **Authentication**: All requests must be signed with your private key
2. **Text-to-Image Process**:
   - Initialize a job with unique request ID
   - Set up image generation parameters (model, prompt, size, etc.)
   - Submit job and monitor status
   - Retrieve generated image

## Telegram Bot Requirements

Our bot will need to:
1. Listen for `/imagine` commands followed by a text prompt
2. Parse the prompt from the message
3. Send the prompt to Tensor Art API
4. Return the generated image to the user

## Implementation Steps

1. **Setup Environment**: Install required libraries and set up environment variables
2. **Authentication Handler**: Create functions to generate API signatures 
3. **API Interaction**: Build functions to interact with Tensor Art API
4. **Telegram Bot Handler**: Setup event listeners and command handlers
5. **Error Handling**: Add proper error handling and user feedback
6. **Deployment**: Prepare for deployment on Heroku with environment variables

## Technical Considerations

1. **API Limitations**: 
   - Rate limits: Tensor Art limits to 5 QPS per account
   - Credit consumption: Each image generation costs credits
   - Request timeout: Long-running generations need status checking

2. **Security**:
   - Secure storage of private keys and API credentials
   - Input validation to prevent injection attacks

3. **Performance**:
   - Asynchronous handling of requests
   - Proper error handling and retries

## Project Structure

```
├── .env                    # Environment variables (not in git)
├── .gitignore              # Git ignore file
├── requirements.txt        # Dependencies
├── Procfile                # For Heroku deployment
├── README.md               # Project documentation
├── bot.py                  # Main Telegram bot file
├── config.py               # Configuration and environment loading
├── tams_api/
│   ├── __init__.py
│   ├── client.py           # API client for Tensor Art
│   ├── auth.py             # Authentication and signature generation
│   └── models.py           # Data models for API requests/responses
└── utils/
    ├── __init__.py
    └── helpers.py          # Utility functions
```

This structure provides a clean separation of concerns and makes the code maintainable for future enhancements.
