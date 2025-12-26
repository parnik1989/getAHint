from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "getAHintService"
    debug: bool = True

settings = Settings()
