# =============================================================================
# Google Drive MCP Server - OAuth 2.0 Authentication
# =============================================================================
"""
OAuth 2.0 authentication handler for Google Drive API.

Implements the Desktop App OAuth flow with automatic token refresh
and secure token storage.

Supports multiple authentication methods:
1. Existing token file (from previous auth)
2. Refresh token from environment variable (for containerized deployments)
3. Interactive OAuth flow (for local development)
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",  # Create/access files created by app
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # View file metadata
]

# Environment variable name for refresh token
REFRESH_TOKEN_ENV_VAR = "GOOGLE_DRIVE_REFRESH_TOKEN"


class DriveAuthManager:
    """
    Manages Google OAuth 2.0 authentication for Drive.

    Handles the OAuth flow, token storage, and automatic refresh.

    Attributes:
        client_id: OAuth client ID.
        client_secret: OAuth client secret.
        token_path: Path to store/retrieve tokens.
        oauth_port: Port for OAuth callback server.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_path: str = "drive_token.json",
        oauth_port: int = 8088,
    ) -> None:
        """
        Initialize the auth manager.

        Args:
            client_id: Google OAuth client ID.
            client_secret: Google OAuth client secret.
            token_path: Path to store the token file.
            oauth_port: Port for the OAuth callback server.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = Path(token_path)
        self.oauth_port = oauth_port
        self._credentials: Optional[Credentials] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        creds = self._load_credentials()
        return creds is not None and creds.valid

    @property
    def needs_refresh(self) -> bool:
        """Check if credentials need refresh."""
        creds = self._load_credentials()
        return creds is not None and creds.expired and creds.refresh_token

    def _get_client_config(self) -> dict:
        """Generate OAuth client configuration."""
        return {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [
                    f"http://localhost:{self.oauth_port}",
                    "http://localhost",
                ],
            }
        }

    def _load_credentials(self) -> Optional[Credentials]:
        """
        Load credentials from token file or environment variable.

        Priority order:
        1. Existing token file
        2. Refresh token from environment variable
        """
        if self._credentials is not None:
            return self._credentials

        # Try loading from token file first
        if self.token_path.exists():
            try:
                with open(self.token_path, "r") as f:
                    token_data = json.load(f)

                self._credentials = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes"),
                )
                logger.debug(f"Loaded credentials from {self.token_path}")
                return self._credentials

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error loading token file: {e}")

        # Try building from refresh token environment variable
        refresh_token = os.environ.get(REFRESH_TOKEN_ENV_VAR)
        if refresh_token:
            logger.info(
                f"Building credentials from {REFRESH_TOKEN_ENV_VAR} environment variable"
            )
            self._credentials = self._build_credentials_from_refresh_token(
                refresh_token
            )
            if self._credentials:
                # Save to token file for future use
                self._save_credentials(self._credentials)
                return self._credentials

        logger.debug(f"No credentials found (no token file, no {REFRESH_TOKEN_ENV_VAR})")
        return None

    def _build_credentials_from_refresh_token(
        self, refresh_token: str
    ) -> Optional[Credentials]:
        """
        Build credentials from a refresh token.

        This allows containerized deployments to authenticate using a refresh token
        stored as an environment variable, without needing interactive OAuth flow.

        Args:
            refresh_token: The OAuth refresh token.

        Returns:
            Valid Credentials object or None if refresh fails.
        """
        try:
            # Create credentials with just the refresh token
            creds = Credentials(
                token=None,  # Will be fetched on first refresh
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=SCOPES,
            )

            # Immediately refresh to get a valid access token
            logger.info("Refreshing credentials from refresh token...")
            creds.refresh(Request())

            logger.info("Successfully built credentials from refresh token")
            return creds

        except RefreshError as e:
            logger.error(f"Failed to refresh credentials from token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error building credentials from refresh token: {e}")
            return None

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }

        with open(self.token_path, "w") as f:
            json.dump(token_data, f, indent=2)

        logger.info(f"Credentials saved to {self.token_path}")

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, refreshing if necessary.

        Returns:
            Valid Credentials object or None if authentication required.
        """
        creds = self._load_credentials()

        if creds is None:
            logger.info("No credentials found, authentication required")
            return None

        if creds.valid:
            return creds

        if creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
                self._save_credentials(creds)
                self._credentials = creds
                return creds
            except RefreshError as e:
                logger.error(f"Failed to refresh credentials: {e}")
                return None

        return None

    def authenticate(self) -> Credentials:
        """
        Run the OAuth authentication flow.

        Opens a browser for user authentication and returns credentials.

        Returns:
            Valid Credentials object.

        Raises:
            Exception: If authentication fails.
        """
        client_config = self._get_client_config()

        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=SCOPES,
        )

        logger.info(f"Starting OAuth flow on port {self.oauth_port}")

        # Run local server for OAuth callback
        creds = flow.run_local_server(
            port=self.oauth_port,
            prompt="consent",
            access_type="offline",
        )

        self._save_credentials(creds)
        self._credentials = creds

        logger.info("Authentication successful")
        return creds

    def revoke(self) -> bool:
        """
        Revoke current credentials and delete token file.

        Returns:
            True if revocation successful, False otherwise.
        """
        creds = self._load_credentials()

        if creds is None:
            logger.info("No credentials to revoke")
            return True

        try:
            import httpx

            response = httpx.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": creds.token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                logger.info("Token revoked successfully")
            else:
                logger.warning(f"Token revocation returned: {response.status_code}")

        except Exception as e:
            logger.error(f"Error revoking token: {e}")

        if self.token_path.exists():
            self.token_path.unlink()
            logger.info(f"Deleted token file: {self.token_path}")

        self._credentials = None
        return True

    def get_auth_url(self) -> str:
        """
        Get the OAuth authorization URL for manual authentication.

        Returns:
            Authorization URL string.
        """
        client_config = self._get_client_config()

        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=f"http://localhost:{self.oauth_port}",
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        return auth_url
