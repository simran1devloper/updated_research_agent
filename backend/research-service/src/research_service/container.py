"""DI container for the Research Service."""
from dependency_injector import containers, providers
from shared.config import GrpcHosts, ResearchSettings

from .adapters.outbound.intent_client import IntentServiceClient
from .adapters.outbound.memory_client import MemoryServiceClient
from .adapters.outbound.search_client import SearchServiceClient
from .adapters.outbound.synthesis_client import SynthesisServiceClient
from .adapters.outbound.conversation_client import ConversationServiceClient
from .graph.builder import build_research_graph
from .application.use_cases import RunResearchUseCase, StreamResearchUseCase


class ResearchContainer(containers.DeclarativeContainer):
    grpc_hosts = providers.Singleton(GrpcHosts)
    research_settings = providers.Singleton(ResearchSettings)

    intent_client = providers.Singleton(
        IntentServiceClient,
        grpc_host=grpc_hosts.provided.intent_host,
        grpc_port=grpc_hosts.provided.intent_grpc_port,
    )
    memory_client = providers.Singleton(
        MemoryServiceClient,
        grpc_host=grpc_hosts.provided.memory_host,
        grpc_port=grpc_hosts.provided.memory_grpc_port,
    )
    search_client = providers.Singleton(
        SearchServiceClient,
        grpc_host=grpc_hosts.provided.search_host,
        grpc_port=grpc_hosts.provided.search_grpc_port,
    )
    synthesis_client = providers.Singleton(
        SynthesisServiceClient,
        grpc_host=grpc_hosts.provided.synthesis_host,
        grpc_port=grpc_hosts.provided.synthesis_grpc_port,
    )
    conversation_client = providers.Singleton(
        ConversationServiceClient,
        grpc_host=grpc_hosts.provided.conversation_host,
        grpc_port=grpc_hosts.provided.conversation_grpc_port,
    )

    research_graph = providers.Singleton(
        build_research_graph,
        intent_port=intent_client,
        memory_port=memory_client,
        search_port=search_client,
        synthesis_port=synthesis_client,
        conversation_port=conversation_client,
    )

    run_research_use_case = providers.Factory(
        RunResearchUseCase,
        compiled_graph=research_graph,
    )
    stream_research_use_case = providers.Factory(
        StreamResearchUseCase,
        compiled_graph=research_graph,
        synthesis_port=synthesis_client,
        conversation_port=conversation_client,
    )

    _instance: "ResearchContainer | None" = None

    @classmethod
    def instance(cls) -> "ResearchContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
