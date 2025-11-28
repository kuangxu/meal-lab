#!/bin/bash

# Activate virtual environment and run the Flask application
source venv/bin/activate

# Use the Python executable from the venv directly (most reliable)
exec venv/bin/python app.py
