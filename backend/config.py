import yaml
from pathlib import Path

class Config:
    """Singleton configuration loader using a YAML file.
    Loads ``config.yaml`` from the project root (workspace directory).
    """
    _instance = None
    _config_path = Path(__file__).resolve().parents[1] / "config.yaml"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        if not self._config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Sections with defaults
        self.ingestion = data.get("ingestion", {})
        self.retrieval = data.get("retrieval", {})
        self.analytics = data.get("analytics", {})
        self.server = data.get("server", {})
        self.cache = data.get("cache", {})
        # Frequently used values
        self.chunk_size = self.ingestion.get("chunk_size", 400)
        self.chunk_overlap = self.ingestion.get("chunk_overlap", 50)
        self.supported_file_types = set(self.ingestion.get("supported_file_types", ["pdf", "docx", "txt", "csv"]))
        self.embedding_model = self.retrieval.get("embedding_model", "all-MiniLM-L6-v2")
        self.faiss_index_type = self.retrieval.get("faiss_index_type", "flat")
        self.index_path = Path(self.retrieval.get("index_path", "data/vector_store/index.faiss"))
        self.analytics_db_path = Path(self.analytics.get("db_path", "data/analytics/analytics.db"))
        self.analytics_export_path = Path(self.analytics.get("export_path", "data/analytics/export.csv"))
        self.cache_maxsize = self.cache.get("maxsize", 500)
        self.async_server = self.server.get("async_server", "hypercorn")
        # Resolve relative to project root
        root = self._config_path.parent
        self.index_path = (root / self.index_path).resolve()
        self.analytics_db_path = (root / self.analytics_db_path).resolve()
        self.analytics_export_path = (root / self.analytics_export_path).resolve()

# Export a singleton instance for easy import
config = Config()
