"""DI container for the Auth Service."""
from dependency_injector import containers, providers

from .adapters.outbound.user_repository import SQLUserRepository
from .adapters.outbound.token_repository import SQLRefreshTokenRepository
from .adapters.outbound.jwt_service import JWTTokenService
from .adapters.outbound.password_hasher import BcryptHasher
from .domain.service import AuthDomainService
from .application.use_cases import (
    RegisterUseCase, LoginUseCase, RefreshUseCase, LogoutUseCase,
    OAuthLoginUseCase, ValidateTokenUseCase,
    GetUserUseCase, ListUsersUseCase, UpdateUserUseCase, DeleteUserUseCase,
)


class AuthContainer(containers.DeclarativeContainer):
    # Adapters
    user_repo = providers.Singleton(SQLUserRepository)
    token_repo = providers.Singleton(SQLRefreshTokenRepository)
    token_svc = providers.Singleton(JWTTokenService)
    hasher = providers.Singleton(BcryptHasher)

    # Domain service
    auth_svc = providers.Singleton(
        AuthDomainService,
        user_repo=user_repo,
        token_repo=token_repo,
        token_svc=token_svc,
        hasher=hasher,
    )

    # Use-cases
    register_use_case = providers.Factory(RegisterUseCase, svc=auth_svc)
    login_use_case = providers.Factory(LoginUseCase, svc=auth_svc)
    refresh_use_case = providers.Factory(RefreshUseCase, svc=auth_svc)
    logout_use_case = providers.Factory(LogoutUseCase, svc=auth_svc)
    oauth_login_use_case = providers.Factory(OAuthLoginUseCase, svc=auth_svc)
    validate_token_use_case = providers.Factory(ValidateTokenUseCase, svc=auth_svc)

    get_user_use_case = providers.Factory(GetUserUseCase, repo=user_repo)
    list_users_use_case = providers.Factory(ListUsersUseCase, repo=user_repo)
    update_user_use_case = providers.Factory(UpdateUserUseCase, repo=user_repo)
    delete_user_use_case = providers.Factory(DeleteUserUseCase, repo=user_repo)

    _instance: "AuthContainer | None" = None

    @classmethod
    def instance(cls) -> "AuthContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
