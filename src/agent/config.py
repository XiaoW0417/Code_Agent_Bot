import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class Settings:
    openai_api_key: str | None
    openai_base_url: str | None
    model_name: str | None

def load_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[2] / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    model_name = os.getenv('OPENAI_MODEL_NAME')

    return Settings(
        openai_api_key=api_key,
        openai_base_url=base_url,
        model_name=model_name
    )

settings = load_settings()

    