import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # NASA FIRMS - Free key from https://firms.modaps.eosdis.nasa.gov/api/
    NASA_FIRMS_KEY: str = os.getenv("NASA_FIRMS_KEY", "DEMO_KEY")
    
    # LLM - Groq (free) or OpenAI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Ollama (local, no key needed)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    
    # LLM provider: "groq", "openai", "ollama"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    
    # DB
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./earth_intel.db")
    
    # App
    CORS_ORIGINS: list = ["*"]
    DEFAULT_REGION: str = "india"  # Default map focus
    
    # India bounding box (lon_min,lat_min,lon_max,lat_max)
    INDIA_BBOX: str = "68.0,8.0,97.5,37.5"

settings = Settings()
