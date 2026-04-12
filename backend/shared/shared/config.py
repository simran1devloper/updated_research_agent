"""
Centralized settings loaded from environment variables.
Each service imports only what it needs from here.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_", extra="ignore")

    base_url: str = "http://192.168.196.22:11434"
    model_name: str = "ministral-3:latest"
    timeout: int = 120


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")

    path: str = "./qdrant_db"
    collection: str = "research_memory"


class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    tavily_api_key: str = ""
    google_api_key: str = ""
    google_cse_id: str = ""


class ResearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESEARCH_", extra="ignore")

    max_iterations: int = 3
    confidence_threshold: float = 0.8
    max_tokens_per_query: int = 5000
    output_dir: str = "./output"


class ServiceURLs(BaseSettings):
    """HTTP URLs — used by API Gateway and for direct REST testing."""
    model_config = SettingsConfigDict(env_prefix="SERVICE_", extra="ignore")

    intent_url: str = "http://intent-service:8001"
    memory_url: str = "http://memory-service:8002"
    search_url: str = "http://search-service:8003"
    synthesis_url: str = "http://synthesis-service:8004"
    research_url: str = "http://research-service:8005"


class GrpcHosts(BaseSettings):
    """gRPC host/port config — used by research-service to call internal services."""
    model_config = SettingsConfigDict(env_prefix="GRPC_", extra="ignore")

    intent_host: str = "intent-service"
    intent_grpc_port: int = 50051

    memory_host: str = "memory-service"
    memory_grpc_port: int = 50052

    search_host: str = "search-service"
    search_grpc_port: int = 50053

    synthesis_host: str = "synthesis-service"
    synthesis_grpc_port: int = 50054

    auth_host: str = "auth-service"
    auth_grpc_port: int = 50055

    conversation_host: str = "conversation-service"
    conversation_grpc_port: int = 50056
