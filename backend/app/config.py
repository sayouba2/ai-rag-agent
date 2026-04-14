import os
from pathlib import Path
from dotenv import load_dotenv

# Charge d'abord le .env à la racine du projet (deux niveaux au-dessus de ce fichier),
# puis le .env local du backend s'il existe (override possible).
_root_env = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_root_env)
load_dotenv()  # .env local backend (override si présent)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
DATA_DIR = os.getenv("DATA_DIR", "data")

# Origines autorisées pour le CORS — en prod, remplacer par l'URL du frontend
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Taille maximale des fichiers uploadés (défaut : 50 Mo)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Extensions autorisées
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md", ".csv"}

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")
