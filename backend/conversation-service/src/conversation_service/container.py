"""DI container for the Conversation Service."""
from dependency_injector import containers, providers
from .adapters.outbound.repositories import SQLThreadRepository, SQLMessageRepository
from .application.use_cases import (
    EnsureThreadUseCase, AppendMessageUseCase, GetHistoryUseCase,
    ListThreadsUseCase, DeleteThreadUseCase,
)


class ConversationContainer(containers.DeclarativeContainer):
    thread_repo = providers.Singleton(SQLThreadRepository)
    msg_repo = providers.Singleton(SQLMessageRepository)

    ensure_thread_use_case = providers.Factory(EnsureThreadUseCase, repo=thread_repo)
    append_message_use_case = providers.Factory(
        AppendMessageUseCase, thread_repo=thread_repo, msg_repo=msg_repo
    )
    get_history_use_case = providers.Factory(GetHistoryUseCase, repo=msg_repo)
    list_threads_use_case = providers.Factory(ListThreadsUseCase, repo=thread_repo)
    delete_thread_use_case = providers.Factory(
        DeleteThreadUseCase, thread_repo=thread_repo, msg_repo=msg_repo
    )

    _instance: "ConversationContainer | None" = None

    @classmethod
    def instance(cls) -> "ConversationContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
