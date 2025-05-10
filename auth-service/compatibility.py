from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import grpc
from auth_pb2 import (
    LoginRequest as GrpcLoginRequest,
    LogoutRequest as GrpcLogoutRequest,
    RefreshRequest as GrpcRefreshRequest,
    ValidationRequest as GrpcValidationRequest
)
from auth_pb2_grpc import AuthServiceStub
import logging

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# gRPC channel setup
channel = grpc.insecure_channel('localhost:50051')
auth_client = AuthServiceStub(channel)

@app.post("/auth/login")
async def login(username: str, password: str):
    try:
        grpc_request = GrpcLoginRequest(username=username, password=password)
        response = auth_client.Login(grpc_request)
        return {
            "access_token": response.access_token,
            "refresh_token": response.refresh_token,
            "token_type": "bearer",
            "roles": response.roles,
            "expires_in": response.expires_in
        }
    except grpc.RpcError as e:
        logging.error(f"gRPC error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@app.post("/auth/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    try:
        grpc_request = GrpcLogoutRequest(token=token)
        response = auth_client.Logout(grpc_request)
        return {"message": "Successfully logged out"}
    except grpc.RpcError as e:
        logging.error(f"gRPC error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@app.post("/auth/refresh-token")
async def refresh_token(refresh_token: str):
    try:
        grpc_request = GrpcRefreshRequest(refresh_token=refresh_token)
        response = auth_client.RefreshToken(grpc_request)
        return {
            "access_token": response.access_token,
            "token_type": "bearer"
        }
    except grpc.RpcError as e:
        logging.error(f"gRPC error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@app.get("/auth/validate")
async def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        grpc_request = GrpcValidationRequest(token=token)
        response = auth_client.ValidateToken(grpc_request)
        return {
            "valid": response.valid,
            "username": response.username,
            "roles": response.roles
        }
    except grpc.RpcError as e:
        logging.error(f"gRPC error during token validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )