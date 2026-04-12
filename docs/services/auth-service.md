# Auth Service

**Port:** 8007 (HTTP) | 50055 (gRPC)  
**Role:** Identity provider — handles registration, login, token lifecycle, and OAuth.

## Responsibilities
- User registration and credential management (bcrypt password hashing)
- JWT access token + refresh token issuance and rotation
- OAuth 2.0 login via Google and GitHub (auto-provisions accounts)
- Token validation exposed over gRPC for the API Gateway
- Admin user management (list, get, update, delete users)

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create new account |
| POST | `/auth/login` | Email/password login → token pair |
| POST | `/auth/refresh` | Rotate refresh token → new token pair |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/oauth/{provider}` | Redirect to Google/GitHub OAuth |
| GET | `/auth/oauth/{provider}/callback` | OAuth callback → redirect to frontend with tokens |
| GET | `/users` | List all users (admin) |
| GET | `/users/{id}` | Get user by ID |
| PATCH | `/users/{id}` | Update username / role / active status |
| DELETE | `/users/{id}` | Delete user |
| GET | `/auth/health` | Health check |

## gRPC Interface
- `ValidateToken(token)` → `TokenClaims` — used exclusively by the API Gateway middleware

## Token Strategy
- Access token: short-lived JWT (default 30 min), signed with `JWT_SECRET`
- Refresh token: long-lived JWT (default 7 days), stored as SHA-256 hash in SQLite
- On refresh: old token is revoked, new pair issued (rotation)
- On logout: refresh token hash deleted from DB

## OAuth Flow
1. Browser hits `/auth/oauth/google` → redirected to provider
2. Provider redirects to `/auth/oauth/google/callback?code=...`
3. Service exchanges code for provider token, fetches user info
4. Auto-provisions or links account, issues JWT pair
5. Redirects browser to `FRONTEND_URL/auth/callback?access_token=...&refresh_token=...`

## Domain Model
- `User` — id, email, username, role (USER/ADMIN), is_active, hashed_password, oauth_provider, oauth_sub
- `TokenPair` — access_token, refresh_token
- `TokenClaims` — user_id, email, role, valid, error

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/service.py` — pure business logic (AuthDomainService)
- `domain/ports.py` — abstract interfaces (IUserRepository, ITokenService, IPasswordHasher, IRefreshTokenRepository)
- `adapters/inbound/http_router.py` — FastAPI REST endpoints
- `adapters/inbound/grpc_server.py` — gRPC token validation server
- `adapters/outbound/user_repository.py` — SQLAlchemy/SQLite user store
- `adapters/outbound/token_repository.py` — SQLAlchemy/SQLite refresh token store
- `adapters/outbound/jwt_service.py` — PyJWT token creation/validation
- `adapters/outbound/password_hasher.py` — bcrypt adapter
- `db/` — SQLAlchemy async session + table definitions

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:////data/auth.db` | Auth database |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `JWT_ACCESS_TTL_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TTL_DAYS` | `7` | Refresh token TTL |
| `AUTH_BASE_URL` | `http://localhost:8007` | Used to build OAuth redirect URIs |
| `FRONTEND_URL` | `http://localhost:3000` | OAuth success redirect target |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | — | Google OAuth credentials |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | — | GitHub OAuth credentials |
