from fastapi import APIRouter, Depends, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json
import requests
import logging

from ..database import get_db
from ..models.user import User
from ..models.session import Session, SuspiciousActivity as SuspiciousActivityModel # SQLAlchemy models, aliased
from ..schemas.session import SessionOut, SessionTerminate, SuspiciousActivityCreate # Pydantic schemas
from ..schemas.admin import AdminUserOut
from ..auth_utils import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

# WebSocket manager for real-time updates
class SessionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

session_manager = SessionManager()

def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation data for IP address"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        logging.error(f"Geolocation lookup failed: {str(e)}")
        return {}

@router.get("/sessions", response_model=List[SessionOut])
async def list_active_sessions(
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """List all active sessions (optionally filtered by user)"""
    query = db.query(Session).filter(Session.is_active == True)
    if user_id:
        query = query.filter(Session.user_id == user_id)
    return query.all()

@router.post("/sessions/terminate")
async def terminate_session(
    termination: SessionTerminate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Terminate a session by ID"""
    session = db.query(Session).filter(Session.id == termination.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    session.terminated_by_admin = True
    db.commit()
    
    # Broadcast termination to all connected clients
    await session_manager.broadcast({
        "event": "session_terminated",
        "session_id": session.id,
        "terminated_by": current_user.username
    })
    
    return {"message": "Session terminated successfully"}

@router.websocket("/sessions/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time session updates"""
    await session_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(websocket)

@router.post("/sessions/suspicious")
async def report_suspicious_activity(
    activity: SuspiciousActivityCreate, # Use Pydantic model for request body
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Report suspicious session activity"""
    # Create the SQLAlchemy model instance from the Pydantic model
    db_activity = SuspiciousActivityModel(
        session_id=activity.session_id,
        activity_type=activity.activity_type,
        details=activity.details,
        severity=activity.severity
        # created_at will be default
    )
    
    # Add to session and commit (assuming you want to save this reported activity)
    # If you only want to mark the main Session as suspicious, this part might differ.
    # For now, let's assume we are creating a new SuspiciousActivity entry.
    db.add(db_activity)
    
    # Mark the main session as suspicious
    db_session_to_mark = db.query(Session).filter(Session.id == activity.session_id).first()
    if not db_session_to_mark:
        # Rollback if the main session isn't found, as we added db_activity
        db.rollback()
        raise HTTPException(status_code=404, detail="Session to mark as suspicious not found")
    
    db_session_to_mark.is_suspicious = True
    db.commit()
    # It's good practice to refresh the instance if you return it or parts of it
    db.refresh(db_activity)
    db.refresh(db_session_to_mark)
    
    return {"message": "Suspicious activity reported and session marked.", "activity_id": db_activity.id}
    
    # Broadcast suspicious activity to all connected clients
    await session_manager.broadcast({
        "event": "suspicious_activity",
        "session_id": session.id,
        "activity_type": activity.activity_type,
        "severity": activity.severity
    })
    
    return {"message": "Suspicious activity reported"}