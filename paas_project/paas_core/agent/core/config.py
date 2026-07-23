import os


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "qwe")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://112.132.229.234:8030/v1")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "DeepSeek-R1-Distill-Qwen-671B")
    CHECKPOINT_DB = os.getenv(
        "PAA_LANGGRAPH_CHECKPOINT_DB", "database/langgraph_checkpoints.sqlite"
    )


settings = Config()
