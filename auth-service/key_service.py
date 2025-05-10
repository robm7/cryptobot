from concurrent import futures
import logging
import grpc
from typing import Dict, Optional
from key_manager import KeyManager
import auth_pb2
import auth_pb2_grpc
import redis

logger = logging.getLogger(__name__)

class KeyManagementService(auth_pb2_grpc.KeyManagementServiceServicer):
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.key_manager = KeyManager(self.redis)

    def RotateKey(self, request: auth_pb2.RotateKeyRequest, context: grpc.ServicerContext) -> auth_pb2.RotateKeyResponse:
        try:
            key_id = self.key_manager.rotate_keys(request.expire_in_days)
            key = self.key_manager.get_key(key_id)
            return auth_pb2.RotateKeyResponse(
                key_id=key['id'],
                expires_at=key['expires_at']
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.RotateKeyResponse()

    def GetCurrentKey(self, request: auth_pb2.GetCurrentKeyRequest, context: grpc.ServicerContext) -> auth_pb2.KeyResponse:
        try:
            key = self.key_manager.get_current_key()
            if not key:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return auth_pb2.KeyResponse()
            return self._key_to_proto(key)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.KeyResponse()

    def GetKey(self, request: auth_pb2.GetKeyRequest, context: grpc.ServicerContext) -> auth_pb2.KeyResponse:
        try:
            key = self.key_manager.get_key(request.key_id)
            if not key:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return auth_pb2.KeyResponse()
            return self._key_to_proto(key)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.KeyResponse()

    def ListKeys(self, request: auth_pb2.ListKeysRequest, context: grpc.ServicerContext) -> auth_pb2.ListKeysResponse:
        try:
            keys = self.key_manager.get_all_keys()
            return auth_pb2.ListKeysResponse(
                keys=[self._key_to_proto(key) for key in keys]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.ListKeysResponse()

    def RevokeKey(self, request: auth_pb2.RevokeKeyRequest, context: grpc.ServicerContext) -> auth_pb2.RevokeKeyResponse:
        try:
            success = self.key_manager.revoke_key(request.key_id)
            return auth_pb2.RevokeKeyResponse(success=success)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.RevokeKeyResponse()

    def GetExpiringKeys(self, request: auth_pb2.GetExpiringKeysRequest, context: grpc.ServicerContext) -> auth_pb2.ExpiringKeysResponse:
        try:
            keys = self.key_manager.get_upcoming_expirations(request.days)
            return auth_pb2.ExpiringKeysResponse(
                keys=[self._key_to_proto(key) for key in keys]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.ExpiringKeysResponse()

    def GetPermissions(self, request: auth_pb2.GetPermissionsRequest, context: grpc.ServicerContext) -> auth_pb2.GetPermissionsResponse:
        try:
            permissions = self.key_manager.get_permissions(request.key_id)
            return auth_pb2.GetPermissionsResponse(permissions=permissions)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.GetPermissionsResponse()

    def UpdatePermissions(self, request: auth_pb2.UpdatePermissionsRequest, context: grpc.ServicerContext) -> auth_pb2.UpdatePermissionsResponse:
        try:
            success = self.key_manager.update_key_permissions(
                request.key_id,
                request.permissions
            )
            return auth_pb2.UpdatePermissionsResponse(success=success)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return auth_pb2.UpdatePermissionsResponse()

    def _key_to_proto(self, key: Dict) -> auth_pb2.KeyResponse:
        return auth_pb2.KeyResponse(
            key_id=key['id'],
            created_at=key['created_at'],
            expires_at=key['expires_at'],
            is_active=key['is_active'],
            is_revoked=key['is_revoked'],
            version=key['version']
        )

def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_KeyManagementServiceServicer_to_server(
        KeyManagementService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("Key Management Service started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()