#!/bin/bash
# Render.com start script for Discord Bot

# Install dependencies
pip install -r requirements.txt

# Run the application
gunicorn --bind 0.0.0.0:$PORT --reuse-port --reload main:app