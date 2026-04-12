"""
Dependency Injection container for the Intent Service.
Uses dependency-injector to wire ports → adapters → use-cases.
"""
from dependency_injector import containers, providers

from shared.config import OllamaSettings

from .adapters.outbound.ollama_adapter import OllamaLLMAdapter
from .domain.service import IntentDomainService
from .application.use_cases import ClassifyIntentUseCase


class IntentContainer(containers.DeclarativeContainer):
    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------
    config = providers.Singleton(OllamaSettings)

    # -------------------------------------------------------------------------
    # Outbound adapters
    # -------------------------------------------------------------------------
    llm_adapter = providers.Singleton(
        OllamaLLMAdapter,
        base_url=config.provided.base_url,
        model_name=config.provided.model_name,
        timeout=config.provided.timeout,
    )

    # -------------------------------------------------------------------------
    # Domain service  (wired with outbound port)
    # -------------------------------------------------------------------------
    intent_domain_service = providers.Singleton(
        IntentDomainService,
        llm_port=llm_adapter,
    )

    # -------------------------------------------------------------------------
    # Application use-cases  (wired with domain service)
    # -------------------------------------------------------------------------
    classify_intent_use_case = providers.Factory(
        ClassifyIntentUseCase,
        classifier=intent_domain_service,
    )

    # -------------------------------------------------------------------------
    # Singleton accessor used by the inbound adapter
    # -------------------------------------------------------------------------
    _instance: "IntentContainer | None" = None

    @classmethod
    def instance(cls) -> "IntentContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
