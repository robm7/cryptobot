import grpc
from concurrent import futures
from datetime import datetime
from typing import List, Optional
from .auth_pb2 import ( # Corrected import
    KeyResponse,
    ListKeysResponse,
    RevokeKeyResponse
)
from .auth_pb2_grpc import ( # Corrected import
    KeyManagementServiceServicer,
    add_KeyManagementServiceServicer_to_server,
    add_UserManagementServiceServicer_to_server
)
from .key_manager import KeyManager # Corrected import
from .user_service import UserService # Corrected import
from .user_manager import UserManager # Corrected import

class AuthService(KeyManagementServiceServicer):
    def __init__(self, redis_client, key_manager: Optional[KeyManager] = None) -> None:
        self.key_manager = key_manager if key_manager else KeyManager(redis_client)

    def GetCurrentKey(self, request, context):
        key = self.key_manager.get_current_key()
        if not key:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No active key found")
            return KeyResponse()
        return self._key_to_response(key)

    def RotateKey(self, request, context):
        try:
            new_key_id = self.key_manager.rotate_keys(request.expire_in_days)
            new_key = self.key_manager.get_key(new_key_id)
            return self._key_to_response(new_key)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return KeyResponse()

    def ListKeys(self, request, context):
        keys = self.key_manager.get_all_keys()
        return ListKeysResponse(keys=[self._key_to_response(k) for k in keys])

    def GetExpiringKeys(self, request, context):
        keys = self.key_manager.get_upcoming_expirations(request.days)
        return ListKeysResponse(keys=[self._key_to_response(k) for k in keys])

    def RevokeKey(self, request, context):
        success = self.key_manager.revoke_key(request.key_id)
        return RevokeKeyResponse(success=success)

    def _key_to_response(self, key_data: dict) -> KeyResponse:
        return KeyResponse(
            key_id=key_data["id"],
            created_at=key_data["created_at"],
            expires_at=key_data["expires_at"],
            is_active=key_data["is_active"],
            is_revoked=key_data["is_revoked"],
            version=key_data["version"],
            permissions=key_data["permissions"]
        )

def serve(redis_client, key_manager: Optional[KeyManager] = None, port: int = 50051, max_retries: int = 5) -> None:
    import logging
    logger = logging.getLogger(__name__)
    
    server = None
    current_port = port
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            
            # Initialize and register Key Management Service
            add_KeyManagementServiceServicer_to_server(
                AuthService(redis_client, key_manager), server)
            
            # Initialize and register User Management Service
            user_manager = UserManager(redis_client)
            user_service = UserService(redis_client, user_manager)
            add_UserManagementServiceServicer_to_server(user_service, server)
            
            # Add health check service
            server.add_generic_rpc_handlers((_HealthServicer(),))
            
            # Try to bind to port
            server.add_insecure_port(f'[::]:{current_port}')
            server.start()
            logger.info(f"gRPC server started on port {current_port}")
            break
            
        except Exception as e:
            if "Address already in use" in str(e):
                retry_count += 1
                current_port += 1
                logger.warning(f"Port {current_port-1} in use, trying {current_port}")
                if server:
                    server.stop(0)
                continue
            logger.error(f"Failed to start server: {str(e)}")
            raise
    
    def graceful_shutdown(signum, frame):
        logger.info("Received shutdown signal")
        if server:
            server.stop(0)
            logger.info("gRPC server stopped gracefully")
        sys.exit(0)
    
    import signal
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    # Health check servicer implementation
    class _HealthServicer(grpc.GenericRpcHandler):
        def service(self, handler_call_details):
            if handler_call_details.method == '/grpc.health.v1.Health/Check':
                return grpc.unary_unary_rpc_method_handler(
                    lambda request, context: health_pb2.HealthCheckResponse(
                        status=health_pb2.HealthCheckResponse.SERVING))
    print(f"Server started on port {port} with both Key and User management services")
    server.wait_for_termination()