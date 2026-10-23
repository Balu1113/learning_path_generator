import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_PERSIST_DIR = (
    _chroma_dir if os.path.isabs(_chroma_dir)
    else os.path.normpath(os.path.join(_PROJECT_ROOT, _chroma_dir))
)

