"""DI container for the Synthesis Service."""
from dependency_injector import containers, providers
from shared.config import OllamaSettings

from .adapters.outbound.ollama_adapter import OllamaLLMAdapter
from .domain.service import SynthesisDomainService
from .application.use_cases import SynthesizeReportUseCase, AnalyzeGapsUseCase, SynthesizeStreamUseCase


class SynthesisContainer(containers.DeclarativeContainer):
    config = providers.Singleton(OllamaSettings)

    llm_adapter = providers.Singleton(
        OllamaLLMAdapter,
        base_url=config.provided.base_url,
        model_name=config.provided.model_name,
        timeout=config.provided.timeout,
    )

    synthesis_domain_service = providers.Singleton(
        SynthesisDomainService,
        llm_port=llm_adapter,
    )

    synthesize_report_use_case = providers.Factory(
        SynthesizeReportUseCase,
        service=synthesis_domain_service,
    )

    synthesize_stream_use_case = providers.Factory(
        SynthesizeStreamUseCase,
        service=synthesis_domain_service,
    )

    analyze_gaps_use_case = providers.Factory(
        AnalyzeGapsUseCase,
        service=synthesis_domain_service,
    )

    _instance: "SynthesisContainer | None" = None

    @classmethod
    def instance(cls) -> "SynthesisContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
