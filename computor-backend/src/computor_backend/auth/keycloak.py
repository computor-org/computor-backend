"""
Keycloak authentication provider implementation.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from jose import jwt, JWTError

from computor_backend.plugins.base import (
    AuthenticationPlugin,
    AuthResult,
    UserInfo,
    PluginConfig,
    PluginMetadata,
    AuthStatus,
    AuthenticationType
)

logger = logging.getLogger(__name__)


class KeycloakConfig(PluginConfig):
    """Keycloak-specific configuration."""
    server_url: str = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180")
    realm: str = os.environ.get("KEYCLOAK_REALM", "master")
    client_id: str = os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend")
    client_secret: str = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
    scopes: list = ["openid"]
    verify_ssl: bool = True


class KeycloakAuthPlugin(AuthenticationPlugin):
    """
    Keycloak authentication provider using OpenID Connect.
    """
    
    def __init__(self, config: Optional[PluginConfig] = None):
        """Initialize Keycloak plugin with configuration."""
        if config is None:
            config = PluginConfig()
        super().__init__(config)
        
        # Convert to KeycloakConfig with environment variables
        self.keycloak_config = KeycloakConfig(
            server_url=config.settings.get("server_url", os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180")),
            realm=config.settings.get("realm", os.environ.get("KEYCLOAK_REALM", "computor")),
            client_id=config.settings.get("client_id", os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend")),
            client_secret=config.settings.get("client_secret", os.environ.get("KEYCLOAK_CLIENT_SECRET", "computor-backend-secret")),
            scopes=config.settings.get("scopes", ["openid"]),
            verify_ssl=config.settings.get("verify_ssl", True)
        )
        self._oidc_config = None
        self._jwks = None
        self._available = False  # Track if Keycloak service is available
    
    @property
    def is_available(self) -> bool:
        """Check if Keycloak service is available."""
        return self._available
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="keycloak",
            version="1.0.0",
            description="Keycloak authentication provider using OpenID Connect",
            author="Computor Team",
            provider_name="Keycloak",
            provider_type=AuthenticationType.OIDC,
            requires=["httpx", "python-jose"],
            homepage="https://www.keycloak.org/"
        )
    
    async def initialize(self) -> None:
        """Initialize the plugin and fetch OIDC configuration."""
        await super().initialize()
        
        # Debug: Log configuration being used
        logger.info(f"Keycloak config - Server: {self.keycloak_config.server_url}")
        logger.info(f"Keycloak config - Realm: {self.keycloak_config.realm}")
        logger.info(f"Keycloak config - Client ID: {self.keycloak_config.client_id}")
        logger.info(f"Keycloak config - Client Secret: {'***' if self.keycloak_config.client_secret else 'NOT SET'}")
        
        # Fetch OpenID configuration
        try:
            await self._fetch_oidc_config()
            logger.info("Keycloak plugin initialized successfully")
            self._available = True
            # Note: JWKS will be fetched on-demand when needed for token verification
        except httpx.ConnectError as e:
            # Keycloak service is not available - this is allowed
            logger.warning(f"Keycloak service is not available: {e}")
            logger.info("Keycloak authentication will be disabled. System will continue without SSO support.")
            self._available = False
            self._oidc_config = None
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak plugin: {type(e).__name__}: {e}")
            logger.error("Exception details:", exc_info=True)
            self._available = False
            raise
    
    async def _fetch_oidc_config(self) -> None:
        """Fetch OpenID Connect configuration from Keycloak with retry logic."""
        well_known_url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}/.well-known/openid-configuration"
        
        logger.info(f"Fetching OIDC config from: {well_known_url}")
        
        # Retry logic for OIDC config fetch
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use more conservative HTTP client settings
                async with httpx.AsyncClient(
                    verify=self.keycloak_config.verify_ssl, 
                    timeout=60.0,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)
                ) as client:
                    response = await client.get(well_known_url)
                    logger.info(f"OIDC config response status: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch OIDC config: {response.status_code} - {response.text}")
                        
                    response.raise_for_status()
                    self._oidc_config = response.json()
                    logger.info("OIDC configuration fetched successfully")
                    return
                    
            except Exception as e:
                logger.warning(f"OIDC config fetch attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("All OIDC config fetch attempts failed")
                    raise
                # Wait before retry
                await asyncio.sleep(2)
    
    async def _fetch_jwks(self) -> None:
        """Fetch JSON Web Key Set from Keycloak with retry logic."""
        if not self._oidc_config:
            await self._fetch_oidc_config()
        
        jwks_uri = self._oidc_config.get("jwks_uri")
        if not jwks_uri:
            raise ValueError("JWKS URI not found in OIDC configuration")
        
        logger.info(f"Fetching JWKS from: {jwks_uri}")
        
        # Retry logic for JWKS fetch
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use a longer timeout and more permissive settings for JWKS
                async with httpx.AsyncClient(
                    verify=self.keycloak_config.verify_ssl, 
                    timeout=60.0,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)
                ) as client:
                    response = await client.get(jwks_uri)
                    logger.info(f"JWKS response status: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch JWKS: {response.status_code} - {response.text}")
                        
                    response.raise_for_status()
                    self._jwks = response.json()
                    logger.info("JWKS fetched successfully")
                    return
                    
            except Exception as e:
                logger.warning(f"JWKS fetch attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("All JWKS fetch attempts failed")
                    raise
                # Wait before retry
                await asyncio.sleep(2)
    
    def get_login_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate Keycloak login URL."""
        if not self._oidc_config:
            raise RuntimeError("Plugin not initialized. Call initialize() first.")
        
        auth_endpoint = self._oidc_config.get("authorization_endpoint")
        if not auth_endpoint:
            raise ValueError("Authorization endpoint not found in OIDC configuration")
        
        params = {
            "client_id": self.keycloak_config.client_id,
            "response_type": "code",
            "scope": " ".join(self.keycloak_config.scopes),
            "redirect_uri": redirect_uri
        }
        
        if state:
            params["state"] = state
        
        # Build URL with query parameters
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{auth_endpoint}?{query_string}"
    
    async def handle_callback(self, code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None) -> AuthResult:
        """
        Handle OAuth callback from Keycloak.
        
        Exchange authorization code for tokens and get user info.
        """
        if not self._available:
            raise RuntimeError("Keycloak service is not available")
        
        try:
            # Exchange code for tokens
            print(f"[DEBUG] Starting token exchange for code: {code[:20]}...")
            tokens = await self._exchange_code_for_tokens(code, redirect_uri)
            print(f"[DEBUG] Token exchange completed")
            
            # Parse ID token to get user info
            id_token = tokens.get("id_token")
            print(f"[DEBUG] ID token present: {bool(id_token)}")
            if not id_token:
                return AuthResult(
                    status=AuthStatus.FAILED,
                    error_message="No ID token received from Keycloak"
                )
            
            # Decode and verify ID token
            claims = await self._verify_and_decode_token(id_token)
            
            # Extract user info from claims
            user_info = UserInfo(
                provider_id=claims.get("sub", ""),
                email=claims.get("email"),
                username=claims.get("preferred_username", claims.get("email", "").split("@")[0]),
                given_name=claims.get("given_name"),
                family_name=claims.get("family_name"),
                full_name=claims.get("name"),
                picture=claims.get("picture"),
                groups=claims.get("groups", []),
                attributes={
                    "email_verified": claims.get("email_verified", False),
                    "realm_access": claims.get("realm_access", {}),
                    "resource_access": claims.get("resource_access", {})
                }
            )
            
            # Calculate token expiration
            expires_at = None
            if "exp" in claims:
                expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
            
            return AuthResult(
                status=AuthStatus.SUCCESS,
                user_info=user_info,
                access_token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                expires_at=expires_at,
                session_data={
                    "token_type": tokens.get("token_type", "Bearer"),
                    "expires_in": tokens.get("expires_in"),
                    "scope": tokens.get("scope", "")
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to handle Keycloak callback: {e}")
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message=str(e)
            )
    
    async def _exchange_code_for_tokens(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        if not self._oidc_config:
            raise RuntimeError("Plugin not initialized")
        
        token_endpoint = self._oidc_config.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Token endpoint not found in OIDC configuration")
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.keycloak_config.client_id,
            "client_secret": self.keycloak_config.client_secret
        }
        
        # Add redirect_uri if provided (required for OAuth2 authorization code flow)
        if redirect_uri:
            data["redirect_uri"] = redirect_uri
        
        # Debug logging - using print to ensure visibility
        print(f"[DEBUG] Token exchange request to: {token_endpoint}")
        print(f"[DEBUG] Request data: {data}")
        print(f"[DEBUG] Redirect URI being sent: {data.get('redirect_uri', 'NOT SET')}")
        logger.info(f"Token exchange request to: {token_endpoint}")
        logger.info(f"Request data: {data}")
        logger.info(f"Redirect URI being sent: {data.get('redirect_uri', 'NOT SET')}")
        
        print("[DEBUG] Creating HTTP client...")
        async with httpx.AsyncClient(
            verify=self.keycloak_config.verify_ssl, 
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)
        ) as client:
            print("[DEBUG] HTTP client created, sending token exchange request...")
            try:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                print(f"[DEBUG] Token exchange response received: {response.status_code}")
                
                # Enhanced error handling
                if response.status_code != 200:
                    logger.error(f"Token exchange failed with status {response.status_code}")
                    logger.error(f"Response body: {response.text}")
                    response.raise_for_status()
                
                result = response.json()
                print(f"[DEBUG] Token exchange successful, received tokens")
                return result
            except Exception as e:
                print(f"[DEBUG] Token exchange error: {type(e).__name__}: {e}")
                raise
    
    async def _verify_and_decode_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token using Keycloak's JWKS."""
        if not self._jwks:
            await self._fetch_jwks()
        
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise JWTError("No key ID found in token header")
        
        # Find the matching key in JWKS
        key = None
        for jwk in self._jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        
        if not key:
            raise JWTError(f"No matching key found for kid: {kid}")
        
        # Verify and decode the token
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.keycloak_config.client_id,
                issuer=f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}",
                options={"verify_at_hash": False}  # Skip at_hash verification
            )
            return claims
        except JWTError as e:
            logger.error(f"Token verification failed: {e}")
            raise
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Direct authentication with username/password (Resource Owner Password Credentials).
        
        Note: This flow should be avoided in production. Use authorization code flow instead.
        """
        if not self._available:
            raise RuntimeError("Keycloak service is not available")
        
        if not self._oidc_config:
            raise RuntimeError("Plugin not initialized")
        
        token_endpoint = self._oidc_config.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Token endpoint not found in OIDC configuration")
        
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message="Username and password required"
            )
        
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": self.keycloak_config.client_id,
            "client_secret": self.keycloak_config.client_secret,
            "scope": " ".join(self.keycloak_config.scopes)
        }
        
        try:
            async with httpx.AsyncClient(verify=self.keycloak_config.verify_ssl) as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 401:
                    return AuthResult(
                        status=AuthStatus.FAILED,
                        error_message="Invalid username or password"
                    )
                
                response.raise_for_status()
                tokens = response.json()
                
                # Handle the tokens like in callback
                return await self.handle_callback("", "")  # Reuse token processing logic
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Authentication failed: {e}")
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message=f"Authentication failed: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return AuthResult(
                status=AuthStatus.ERROR,
                error_message=str(e)
            )
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information using access token."""
        if not self._oidc_config:
            raise RuntimeError("Plugin not initialized")
        
        userinfo_endpoint = self._oidc_config.get("userinfo_endpoint")
        if not userinfo_endpoint:
            raise ValueError("UserInfo endpoint not found in OIDC configuration")
        
        async with httpx.AsyncClient(verify=self.keycloak_config.verify_ssl) as client:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            claims = response.json()
        
        return UserInfo(
            provider_id=claims.get("sub", ""),
            email=claims.get("email"),
            username=claims.get("preferred_username", claims.get("email", "").split("@")[0]),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            full_name=claims.get("name"),
            picture=claims.get("picture"),
            groups=claims.get("groups", []),
            attributes={
                "email_verified": claims.get("email_verified", False),
                "realm_access": claims.get("realm_access", {}),
                "resource_access": claims.get("resource_access", {})
            }
        )
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh access token using refresh token."""
        if not self._oidc_config:
            raise RuntimeError("Plugin not initialized")
        
        token_endpoint = self._oidc_config.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Token endpoint not found in OIDC configuration")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.keycloak_config.client_id,
            "client_secret": self.keycloak_config.client_secret
        }
        
        try:
            async with httpx.AsyncClient(verify=self.keycloak_config.verify_ssl) as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
                
                # Process the new tokens
                return await self.handle_callback("", "")  # Reuse token processing logic
                
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return AuthResult(
                status=AuthStatus.FAILED,
                error_message=f"Token refresh failed: {str(e)}"
            )
    
    async def logout(self, access_token: str) -> bool:
        """Logout user from Keycloak."""
        if not self._oidc_config:
            return False
        
        end_session_endpoint = self._oidc_config.get("end_session_endpoint")
        if not end_session_endpoint:
            # If no end session endpoint, just return success
            return True
        
        try:
            async with httpx.AsyncClient(verify=self.keycloak_config.verify_ssl) as client:
                response = await client.post(
                    end_session_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False