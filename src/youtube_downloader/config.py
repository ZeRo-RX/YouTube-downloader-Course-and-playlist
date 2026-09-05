import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

BASE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")

MAX_QUALITY = 1080
WORKERS = 4
SOCKET_TIMEOUT = 30
ANALYSIS_RETRIES = 2
DOWNLOAD_RETRIES = 5
FRAGMENT_RETRIES = 5
DEFAULT_QUALITY = "best"
DEFAULT_MAX_SIZE_MB = None
REQUEST_DELAY = 1.5