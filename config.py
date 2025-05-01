# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This makes variables defined in .env accessible via os.getenv
load_dotenv()

# Get the Google API key from the environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# You could add other configurations here later if needed