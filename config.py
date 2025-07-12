import os
import platform

# OpenAI Configuration  
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPEN_AI_API_KEY") or "dummy-key-for-development"

# Poppler Configuration
if platform.system() == "Windows":
    POPPLER_PATH = "C:\\Users\\sebas\\OneDrive\\Escritorio\\PDF-BOL-Extractor-AWorks\\poppler\\poppler-24.02.0\\Library\\bin"
else:
    # On Linux, poppler-utils is installed via apt-get and is usually in PATH
    POPPLER_PATH = None  # or '/usr/bin' if your code requires an explicit path

# File Processing
OUTPUT_CSV_NAME = "combined_data.csv"

# Modelss
OPENAI_MODEL = "o3-mini"

# Animation Settings
TYPING_DELAY = 0.03
LOADING_ANIMATION_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"] 