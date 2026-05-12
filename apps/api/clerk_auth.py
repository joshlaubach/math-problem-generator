"""
Clerk JWT verification using JWKS (JSON Web Key Sets).

Uses PyJWT's PyJWKClient to fetch and cache Clerk's public keys automatically.
Keys are cached for 1 hour; re-fetched on cache miss or expiry.

Only active when AUTH_PROVIDER=clerk. Falls back gracefully (returns None)
when CLERK_FRONTEND_API is not configured (e.g. in JWT-mode tests).
"""

from __future__ import annotations

from typing import Optional

# Module-level JWKS client; re-created only when the JWKS URL changes.
_jwks_client = None
_jwks_url_cached: str = ""


def verify_clerk_token(token: str) -> Optional[dict]:
    """
    Verify a Clerk-issued JWT using JWKS.

    Args:
        token: Raw Bearer token from the Authorization header.

    Returns:
        Decoded payload dict on success, None on any verification failure.
    """
    import jwt
    from jwt import PyJWKClient

    from config import CLERK_FRONTEND_API, CLERK_JWKS_URL

    jwks_url = CLERK_JWKS_URL or (
        f"https://{CLERK_FRONTEND_API}/.well-known/jwks.json" if CLERK_FRONTEND_API else ""
    )
    if not jwks_url:
        return None

    try:
        client = _get_jwks_client(jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk session tokens don't use aud
            leeway=10,  # 10-second leeway for clock skew and network latency
        )
        return payload
    except Exception:
        return None


def _get_jwks_client(jwks_url: str):
    """Return a cached PyJWKClient; re-instantiate if URL changed."""
    from jwt import PyJWKClient

    global _jwks_client, _jwks_url_cached
    if _jwks_client is None or _jwks_url_cached != jwks_url:
        # lifespan=3600: PyJWT refreshes the key cache after 3600 seconds
        _jwks_client = PyJWKClient(jwks_url, lifespan=3600)
        _jwks_url_cached = jwks_url
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the JWKS client cache (used in tests)."""
    global _jwks_client, _jwks_url_cached
    _jwks_client = None
    _jwks_url_cached = ""


def update_clerk_user_metadata(clerk_user_id: str, public_metadata: dict) -> bool:
    """
    Update publicMetadata for a Clerk user via the Clerk REST API.

    Used by admin endpoints to keep the frontend role check in sync when
    an admin changes a user's role. Returns True on success, False otherwise.
    """
    import httpx
    from config import CLERK_SECRET_KEY

    if not CLERK_SECRET_KEY:
        return False
    try:
        resp = httpx.patch(
            f"https://api.clerk.com/v1/users/{clerk_user_id}/metadata",
            headers={
                "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={"public_metadata": public_metadata},
            timeout=5.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def fetch_clerk_user_email(clerk_user_id: str) -> Optional[str]:
    """
    Fetch the primary email address for a Clerk user via the Clerk REST API.

    Used during JIT user provisioning so we store a real email instead of a
    placeholder. Returns None when CLERK_SECRET_KEY is absent or the call fails.
    """
    import httpx
    from config import CLERK_SECRET_KEY

    if not CLERK_SECRET_KEY:
        return None
    try:
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            timeout=5.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        primary_id = data.get("primary_email_address_id")
        for entry in data.get("email_addresses", []):
            if entry.get("id") == primary_id:
                return entry.get("email_address")
        emails = data.get("email_addresses", [])
        if emails:
            return emails[0].get("email_address")
    except Exception:
        pass
    return None
