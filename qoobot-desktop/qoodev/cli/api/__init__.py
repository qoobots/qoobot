"""
qoodev API module — REST/gRPC remote call interface for Web/Mobile integration.

Provides:
- qoodev/api/rest/    — REST API endpoints
- qoodev/api/grpc/    — gRPC service definitions
- qoodev/api/         — package init with API client factory
"""

# API client factory
from .rest_client import QooDevRESTClient
from .grpc_client import QooDevGRPCClient

__all__ = ["QooDevRESTClient", "QooDevGRPCClient"]
