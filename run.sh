#!/bin/bash

# Script to run the Tensor Art Telegram Bot

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one based on .env.example."
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        exit 1
    fi
fi

# Run the bot
echo "Starting Tensor Art Telegram Bot..."
python bot.py
