from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "PoultryGuard"
    data_dir: Path = Path("./data")
    storage_dir: Path = Path("./storage")
    database_path: Path = Path("./data/poultryguard.sqlite3")
    model_path: str = "yolov8s.pt"
    custom_model_path: str = ""
    detect_conf: float = 0.10
    image_size: int = 960
    frame_stride: int = 3
    max_upload_mb: int = 500
    save_frames: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "jobs").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "frames").mkdir(parents=True, exist_ok=True)
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings().prepare()
