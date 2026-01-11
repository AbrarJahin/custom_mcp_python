"""Security package.

This package centralizes authentication / authorization logic.

For now, it preserves the existing behavior (optional JWT auth) but places
the implementation under a dedicated namespace, per the project layout goals.
"""

from .jwt import api_key_is_allowed, issue_jwt, require_scopes, verify_jwt_from_header
from .middleware import McpAuthGateMiddleware

__all__ = [
    "api_key_is_allowed",
    "issue_jwt",
    "verify_jwt_from_header",
    "require_scopes",
    "McpAuthGateMiddleware",
]
