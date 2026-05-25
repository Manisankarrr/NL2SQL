from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "barbershopsql"
    llm_provider: str = "openrouter"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    max_result_rows: int = 50
    app_env: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_openrouter(self) -> bool:
        return self.llm_provider == "openrouter"

    @property
    def is_groq(self) -> bool:
        return self.llm_provider == "groq"

    @property
    def has_any_llm_key(self) -> bool:
        return bool(self.openrouter_api_key or self.groq_api_key)

settings = Settings()
