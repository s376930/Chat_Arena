import asyncio
import io
import json
import logging
import os
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import MIN_THINK_CHARS, OPENAI_API_KEY, BASE_DIR, LLM_CONFIG_FILE, PERSONAS_FILE, ADMIN_PASSWORD, DATA_DIR, CONVERSATIONS_DIR, INACTIVITY_TIMEOUT_SECONDS
from .websocket_manager import manager
from .pairing_service import pairing_service
from .storage_service import storage_service
from .models import (
    TopicCreate, TopicUpdate,
    TaskCreate, TaskUpdate,
    ConsentData
)
from .llm import AIManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global AI manager instance
ai_manager: Optional[AIManager] = None


async def handle_ai_message(ai_id: str, think: str, speech: str):
    """Callback when an AI generates a message."""
    global ai_manager

    ai_participant = ai_manager.get_ai_participant(ai_id) if ai_manager else None
    if not ai_participant:
        logger.warning(f"AI message callback for unknown AI: {ai_id}")
        return

    partner_id = ai_participant.state.partner_id
    session_id = ai_participant.state.session_id

    # Format message content (HuggingFace format)
    content = f"<think>{think}</think>{speech}"

    # Store AI message
    storage_service.add_message(
        session_id=session_id,
        role=ai_id,
        content=content
    )

    # Send to human partner (only the speech part)
    timestamp = datetime.utcnow().isoformat() + "Z"
    await manager.send_json(partner_id, {
        "type": "partner_message",
        "content": speech,
        "timestamp": timestamp
    })

    logger.info(f"AI {ai_id} sent message to {partner_id}")


async def pair_with_ai(user_id: str) -> bool:
    """
    Pair a user with an AI participant.
    Returns True if pairing was successful, False otherwise.

    This function handles errors gracefully - if AI creation fails,
    the user remains in the queue for human pairing.
    """
    global ai_manager

    # Check if AI is available (enabled AND has working providers)
    if not ai_manager or not ai_manager.is_available:
        return False

    try:
        # Get topic and tasks
        topic = pairing_service.get_random_topic()
        tasks = pairing_service.get_random_tasks(2)

        if not topic or len(tasks) < 2:
            logger.warning("No topics/tasks available for AI pairing")
            return False

        # Generate session ID
        session_id = pairing_service.generate_session_id()

        # Create AI participant
        ai_participant = await ai_manager.create_ai_participant(
            partner_id=user_id,
            session_id=session_id,
            topic=topic.text,
            task=tasks[1].text,  # AI gets second task
        )

        if not ai_participant:
            logger.warning("Failed to create AI participant, user will wait for human partner")
            return False

        ai_id = ai_participant.ai_id

        # Remove user from queue (atomic)
        await pairing_service.remove_from_queue_atomic(user_id)

        # Update user session
        manager.update_session(
            user_id,
            paired=True,
            partner_id=ai_id,
            session_id=session_id,
            task=tasks[0].text,
            is_ai_partner=True
        )

        # Set initial activity timestamp
        manager.update_activity(user_id)

        # Create AI session record in websocket manager
        manager.create_ai_session(
            ai_id=ai_id,
            partner_id=user_id,
            session_id=session_id,
            persona_id=ai_participant.persona.id,
            persona_name=ai_participant.persona.name,
            provider=ai_participant.provider.name,
            model=ai_participant.provider.model,
            topic=topic.text,
            task=tasks[1].text,
        )

        # Create conversation in storage
        storage_service.create_conversation(
            session_id=session_id,
            topic=topic.text,
            participants=[
                {"user_id": user_id, "task": tasks[0].text},
                {"user_id": ai_id, "task": tasks[1].text}
            ]
        )

        # Notify user they're paired
        await manager.send_json(user_id, {
            "type": "paired",
            "topic": topic.text,
            "task": tasks[0].text,
            "session_id": session_id
        })

        logger.info(f"Paired user {user_id} with AI {ai_id}")
        return True

    except Exception as e:
        logger.error(f"Error pairing user {user_id} with AI: {e}")
        return False


async def delayed_pairing(user_id: str, delay_seconds: int):
    """Schedule a pairing attempt after a delay."""
    await asyncio.sleep(delay_seconds)

    # Check if user is still waiting
    session = manager.get_session(user_id)
    if not session or session.paired:
        return

    # Check if user is still in queue (atomic)
    position = await pairing_service.get_queue_position_atomic(user_id)
    if position == 0:
        return

    # Try normal pairing first
    await try_pairing(user_id)

    # If still not paired and odd user, try AI (using is_available for graceful degradation)
    session = manager.get_session(user_id)
    if session and not session.paired:
        if ai_manager and ai_manager.is_available and ai_manager.force_ai_on_odd_users:
            if await pairing_service.has_odd_user_waiting_atomic():
                await pair_with_ai(user_id)


async def check_inactive_users():
    """Background task to check for and kick inactive users."""
    while True:
        await asyncio.sleep(60)  # Check every minute

        inactive_users = manager.get_inactive_users(INACTIVITY_TIMEOUT_SECONDS)

        for user_id in inactive_users:
            logger.info(f"Kicking inactive user: {user_id}")
            await handle_inactivity_kick(user_id)


async def handle_inactivity_kick(user_id: str):
    """Handle kicking a user due to inactivity."""
    global ai_manager

    session = manager.get_session(user_id)

    if not session:
        return

    # Notify the inactive user
    await manager.send_json(user_id, {"type": "inactivity_kick"})

    if session.paired:
        partner_id = session.partner_id
        session_id = session.session_id
        is_ai_partner = session.is_ai_partner

        if partner_id:
            # Handle AI partner differently
            if is_ai_partner and ai_manager:
                # Remove AI participant
                await ai_manager.remove_ai_participant(partner_id)
                manager.remove_ai_session(partner_id)
            else:
                # Clear partner's pairing atomically first
                cleared_partner = await manager.clear_pairing_atomic(partner_id)

                if cleared_partner is not None:
                    # Notify human partner
                    await manager.send_json(partner_id, {"type": "partner_left"})

                    # Add delay for partner if enabled
                    if ai_manager and ai_manager.pairing_delay_enabled:
                        pairing_service.add_delay(partner_id)

                    # Put partner back in queue (atomic)
                    position = await pairing_service.add_to_queue_atomic(partner_id)
                    await manager.send_json(partner_id, {
                        "type": "waiting",
                        "position": position
                    })

                    # Schedule delayed pairing for partner
                    if ai_manager and ai_manager.pairing_delay_enabled:
                        asyncio.create_task(
                            delayed_pairing(partner_id, ai_manager.reassign_delay_seconds)
                        )
                    else:
                        await try_pairing(partner_id)

        # End conversation if exists
        if session_id:
            await storage_service.end_conversation(session_id)

    # Remove user from queue and clear their session (but don't fully disconnect)
    await pairing_service.remove_from_queue_atomic(user_id)
    pairing_service.remove_delay(user_id)
    await manager.clear_pairing_atomic(user_id)
    # Reset their consent status so they need to rejoin
    manager.update_session(user_id, consented=False, last_activity=None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    global ai_manager

    # Startup
    logger.info("Starting Chat Arena server...")

    # Initialize AI manager
    ai_manager = AIManager(
        llm_config_path=LLM_CONFIG_FILE,
        personas_path=PERSONAS_FILE,
        on_ai_message=handle_ai_message,
    )
    await ai_manager.initialize()

    # Configure pairing delay from settings
    if ai_manager.settings:
        pairing_service.set_delay_seconds(ai_manager.reassign_delay_seconds)

    logger.info("AI Manager initialized")

    # Start background task for checking inactive users
    inactivity_task = asyncio.create_task(check_inactive_users())
    logger.info(f"Inactivity checker started (timeout: {INACTIVITY_TIMEOUT_SECONDS}s)")

    yield

    # Shutdown
    logger.info("Shutting down Chat Arena server...")
    inactivity_task.cancel()
    try:
        await inactivity_task
    except asyncio.CancelledError:
        pass
    if ai_manager:
        await ai_manager.shutdown()


app = FastAPI(title="Chat Arena", version="1.0.0", lifespan=lifespan)

# Mount static files
static_dir = BASE_DIR.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ==================== HTML Routes ====================

@app.get("/")
async def serve_index():
    """Serve the main chat interface."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/admin")
async def serve_admin():
    """Serve the admin page."""
    return FileResponse(str(static_dir / "admin.html"))


# ==================== Consent API ====================

@app.get("/api/consent")
async def get_consent():
    """Get the consent form configuration."""
    consent = await storage_service.load_consent()
    return consent.model_dump()


# ==================== WebSocket Handler ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat functionality."""
    user_id = await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(user_id, data)
    except WebSocketDisconnect:
        await handle_disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error for {user_id}: {e}")
        await handle_disconnect(user_id)


async def handle_message(user_id: str, data: dict):
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    if msg_type == "join":
        await handle_join(user_id, data)
    elif msg_type == "message":
        await handle_chat_message(user_id, data)
    elif msg_type == "reassign":
        await handle_reassign(user_id)
    elif msg_type == "disconnect":
        await handle_disconnect(user_id)


async def handle_join(user_id: str, data: dict):
    """Handle a user joining (after consent)."""
    if not data.get("consent"):
        await manager.send_json(user_id, {
            "type": "error",
            "message": "Consent required to participate"
        })
        return

    manager.update_session(user_id, consented=True)
    manager.update_activity(user_id)  # Track activity

    # Add to queue (atomic)
    position = await pairing_service.add_to_queue_atomic(user_id)

    # Send waiting status
    await manager.send_json(user_id, {
        "type": "waiting",
        "position": position
    })

    # Try to pair
    await try_pairing(user_id)


async def try_pairing(user_id: str):
    """Attempt to pair a user with someone in the queue."""
    global ai_manager

    # Use atomic version to prevent race conditions
    partner_id = await pairing_service.try_pair_atomic(user_id)

    if not partner_id:
        # Check if we should pair with AI (using is_available for graceful degradation)
        if ai_manager and ai_manager.is_available and ai_manager.force_ai_on_odd_users:
            if await pairing_service.has_odd_user_waiting_atomic():
                odd_user = await pairing_service.get_odd_user_atomic()
                if odd_user:
                    await pair_with_ai(odd_user)
        return

    # Get random topic and tasks
    topic = pairing_service.get_random_topic()
    tasks = pairing_service.get_random_tasks(2)

    if not topic or len(tasks) < 2:
        # Put both back in queue if no topics/tasks available
        await pairing_service.add_to_queue_atomic(user_id)
        await pairing_service.add_to_queue_atomic(partner_id)
        await manager.send_json(user_id, {
            "type": "error",
            "message": "No topics or tasks available. Please try again later."
        })
        await manager.send_json(partner_id, {
            "type": "error",
            "message": "No topics or tasks available. Please try again later."
        })
        return

    # Generate session ID
    session_id = pairing_service.generate_session_id()

    # Atomically pair both users - this prevents race conditions
    paired = await manager.pair_users_atomic(
        user_id=user_id,
        partner_id=partner_id,
        session_id=session_id,
        user_task=tasks[0].text,
        partner_task=tasks[1].text
    )

    if not paired:
        # Pairing failed (one user disconnected or already paired)
        # Put the user who initiated back in queue
        await pairing_service.add_to_queue_atomic(user_id)
        logger.warning(f"Atomic pairing failed for {user_id} and {partner_id}")
        return

    # Create conversation in storage
    storage_service.create_conversation(
        session_id=session_id,
        topic=topic.text,
        participants=[
            {"user_id": user_id, "task": tasks[0].text},
            {"user_id": partner_id, "task": tasks[1].text}
        ]
    )

    # Notify both users
    await manager.send_json(user_id, {
        "type": "paired",
        "topic": topic.text,
        "task": tasks[0].text,
        "session_id": session_id
    })

    await manager.send_json(partner_id, {
        "type": "paired",
        "topic": topic.text,
        "task": tasks[1].text,
        "session_id": session_id
    })


async def handle_chat_message(user_id: str, data: dict):
    """Handle a chat message from a user."""
    global ai_manager

    session = manager.get_session(user_id)

    if not session or not session.paired:
        await manager.send_json(user_id, {
            "type": "error",
            "message": "You are not in an active chat session"
        })
        return

    # Verify partner still exists and we are mutually paired
    partner_id = session.partner_id
    if not partner_id:
        await manager.send_json(user_id, {
            "type": "error",
            "message": "Partner connection lost"
        })
        return

    # For non-AI partners, verify mutual pairing to prevent cross-talk
    if not session.is_ai_partner:
        partner_session = manager.get_session(partner_id)
        if not partner_session or partner_session.partner_id != user_id:
            await manager.send_json(user_id, {
                "type": "error",
                "message": "Partner connection lost"
            })
            # Clear the broken pairing
            await manager.clear_pairing_atomic(user_id)
            return

    # Update activity timestamp
    manager.update_activity(user_id)

    think = data.get("think", "")
    speech = data.get("speech", "")

    # Validate think requirement
    if len(think) < MIN_THINK_CHARS:
        await manager.send_json(user_id, {
            "type": "error",
            "message": f"Think field must be at least {MIN_THINK_CHARS} characters"
        })
        return

    if not speech.strip():
        await manager.send_json(user_id, {
            "type": "error",
            "message": "Speech field cannot be empty"
        })
        return

    # Format message content with think tag (HuggingFace format)
    content = f"<think>{think}</think>{speech}"

    # Store message
    storage_service.add_message(
        session_id=session.session_id,
        role=user_id,
        content=content
    )

    timestamp = datetime.utcnow().isoformat() + "Z"

    # Confirm to sender first (so their message appears in UI immediately)
    await manager.send_json(user_id, {
        "type": "message_sent",
        "timestamp": timestamp
    })

    # Check if partner is AI
    if session.is_ai_partner and ai_manager:
        # Forward to AI for response (non-blocking - runs in background)
        asyncio.create_task(
            ai_manager.forward_message_to_ai(partner_id, speech)
        )
    else:
        # Send to human partner (only the speech part)
        # send_to_partner already has partner verification built in
        sent = await manager.send_to_partner(user_id, {
            "type": "partner_message",
            "content": speech,
            "timestamp": timestamp
        })
        if not sent:
            logger.warning(f"Failed to send message from {user_id} to partner {partner_id}")


async def handle_reassign(user_id: str):
    """Handle a user requesting to be reassigned to a new partner."""
    global ai_manager

    session = manager.get_session(user_id)

    if session and session.paired:
        partner_id = session.partner_id
        session_id = session.session_id
        is_ai_partner = session.is_ai_partner

        # Handle AI partner differently
        if is_ai_partner and ai_manager:
            # Remove AI participant
            await ai_manager.remove_ai_participant(partner_id)
            manager.remove_ai_session(partner_id)
        elif partner_id:
            # Clear partner's pairing atomically first to prevent race conditions
            cleared_partner = await manager.clear_pairing_atomic(partner_id)

            # Only proceed if partner still exists
            if cleared_partner is not None:
                # Notify human partner
                await manager.send_json(partner_id, {"type": "partner_left"})

                # Add delay for partner if enabled
                if ai_manager and ai_manager.pairing_delay_enabled:
                    pairing_service.add_delay(partner_id)

                # Put partner back in queue (atomic)
                position = await pairing_service.add_to_queue_atomic(partner_id)
                await manager.send_json(partner_id, {
                    "type": "waiting",
                    "position": position
                })

                # Schedule delayed pairing for partner
                if ai_manager and ai_manager.pairing_delay_enabled:
                    asyncio.create_task(
                        delayed_pairing(partner_id, ai_manager.reassign_delay_seconds)
                    )
                else:
                    await try_pairing(partner_id)

        # End the conversation
        if session_id:
            await storage_service.end_conversation(session_id)

    # Clear user's pairing atomically
    await manager.clear_pairing_atomic(user_id)

    # Add delay for user if enabled
    if ai_manager and ai_manager.pairing_delay_enabled:
        pairing_service.add_delay(user_id)

    # Add to queue (atomic)
    position = await pairing_service.add_to_queue_atomic(user_id)
    await manager.send_json(user_id, {
        "type": "waiting",
        "position": position
    })

    # Schedule delayed pairing for user
    if ai_manager and ai_manager.pairing_delay_enabled:
        asyncio.create_task(
            delayed_pairing(user_id, ai_manager.reassign_delay_seconds)
        )
    else:
        await try_pairing(user_id)


async def handle_disconnect(user_id: str):
    """Handle a user disconnecting."""
    global ai_manager

    session = manager.get_session(user_id)

    if session:
        partner_id = session.partner_id
        session_id = session.session_id
        is_ai_partner = session.is_ai_partner

        if partner_id and session.paired:
            # Handle AI partner differently
            if is_ai_partner and ai_manager:
                # Remove AI participant
                await ai_manager.remove_ai_participant(partner_id)
                manager.remove_ai_session(partner_id)
            else:
                # Clear partner's pairing atomically first to prevent race conditions
                cleared_partner = await manager.clear_pairing_atomic(partner_id)

                # Only proceed if partner still exists and was successfully cleared
                if cleared_partner is not None:
                    # Notify human partner
                    await manager.send_json(partner_id, {"type": "partner_left"})

                    # Add delay for partner if enabled
                    if ai_manager and ai_manager.pairing_delay_enabled:
                        pairing_service.add_delay(partner_id)

                    # Put partner back in queue (atomic)
                    position = await pairing_service.add_to_queue_atomic(partner_id)
                    await manager.send_json(partner_id, {
                        "type": "waiting",
                        "position": position
                    })

                    # Schedule delayed pairing for partner
                    if ai_manager and ai_manager.pairing_delay_enabled:
                        asyncio.create_task(
                            delayed_pairing(partner_id, ai_manager.reassign_delay_seconds)
                        )
                    else:
                        await try_pairing(partner_id)

        # End conversation if exists
        if session_id:
            await storage_service.end_conversation(session_id)

    # Remove from queue and disconnect (atomic)
    await pairing_service.remove_from_queue_atomic(user_id)
    pairing_service.remove_delay(user_id)  # Clean up any pending delay
    manager.disconnect(user_id)


# ==================== Whisper Transcription API ====================

@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio using OpenAI Whisper API."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Whisper API not configured")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Read audio file
        audio_content = await audio.read()

        # Save temporarily
        temp_path = f"/tmp/{audio.filename}"
        with open(temp_path, "wb") as f:
            f.write(audio_content)

        # Transcribe
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        # Clean up
        os.remove(temp_path)

        return {"text": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ==================== Admin API ====================

# Topics
@app.get("/api/admin/topics")
async def list_topics():
    """List all topics."""
    data = await storage_service.load_topics_tasks()
    return [t.model_dump() for t in data.topics]


@app.post("/api/admin/topics")
async def create_topic(topic: TopicCreate):
    """Create a new topic."""
    new_topic = await storage_service.add_topic(topic.text)
    pairing_service.reload_topics_tasks()
    return new_topic.model_dump()


@app.put("/api/admin/topics/{topic_id}")
async def update_topic(topic_id: int, topic: TopicUpdate):
    """Update a topic."""
    updated = await storage_service.update_topic(topic_id, topic.text)
    if not updated:
        raise HTTPException(status_code=404, detail="Topic not found")
    pairing_service.reload_topics_tasks()
    return updated.model_dump()


@app.delete("/api/admin/topics/{topic_id}")
async def delete_topic(topic_id: int):
    """Delete a topic."""
    deleted = await storage_service.delete_topic(topic_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Topic not found")
    pairing_service.reload_topics_tasks()
    return {"status": "deleted"}


# Tasks
@app.get("/api/admin/tasks")
async def list_tasks():
    """List all tasks."""
    data = await storage_service.load_topics_tasks()
    return [t.model_dump() for t in data.tasks]


@app.post("/api/admin/tasks")
async def create_task(task: TaskCreate):
    """Create a new task."""
    new_task = await storage_service.add_task(task.text)
    pairing_service.reload_topics_tasks()
    return new_task.model_dump()


@app.put("/api/admin/tasks/{task_id}")
async def update_task(task_id: int, task: TaskUpdate):
    """Update a task."""
    updated = await storage_service.update_task(task_id, task.text)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    pairing_service.reload_topics_tasks()
    return updated.model_dump()


@app.delete("/api/admin/tasks/{task_id}")
async def delete_task(task_id: int):
    """Delete a task."""
    deleted = await storage_service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    pairing_service.reload_topics_tasks()
    return {"status": "deleted"}


# Consent
@app.get("/api/admin/consent")
async def get_admin_consent():
    """Get consent configuration."""
    consent = await storage_service.load_consent()
    return consent.model_dump()


@app.put("/api/admin/consent")
async def update_consent(consent: ConsentData):
    """Update consent configuration."""
    success = await storage_service.save_consent(consent)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save consent")
    return consent.model_dump()


# ==================== Protected Admin API ====================

def verify_admin_password(x_admin_password: str = Header(None)):
    """Verify admin password from header."""
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return True


class FileContent(BaseModel):
    content: str


@app.post("/api/admin/auth")
async def admin_auth(x_admin_password: str = Header(None)):
    """Authenticate admin access."""
    if x_admin_password == ADMIN_PASSWORD:
        return {"authenticated": True}
    raise HTTPException(status_code=401, detail="Invalid password")


@app.get("/api/admin/data-files")
async def list_data_files(authorized: bool = Depends(verify_admin_password)):
    """List all JSON files in the data folder (excluding conversations)."""
    files = []
    for f in DATA_DIR.iterdir():
        if f.is_file() and f.suffix == '.json':
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return sorted(files, key=lambda x: x["name"])


@app.get("/api/admin/data-files/{filename}")
async def get_data_file(filename: str, authorized: bool = Depends(verify_admin_password)):
    """Get content of a specific data file."""
    # Prevent path traversal
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = DATA_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return {"name": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@app.put("/api/admin/data-files/{filename}")
async def update_data_file(filename: str, file_content: FileContent, authorized: bool = Depends(verify_admin_password)):
    """Update content of a specific data file."""
    # Prevent path traversal
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Validate JSON
        json.loads(file_content.content)

        with open(filepath, 'w') as f:
            f.write(file_content.content)

        # Reload topics/tasks if that file was updated
        if filename == 'topics_tasks.json':
            pairing_service.reload_topics_tasks()

        return {"status": "updated", "name": filename}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@app.get("/api/admin/data-files/{filename}/download")
async def download_data_file(filename: str, authorized: bool = Depends(verify_admin_password)):
    """Download a specific data file."""
    # Prevent path traversal
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = DATA_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type='application/json'
    )


@app.post("/api/admin/data-files/upload")
async def upload_data_file(file: UploadFile = File(...), authorized: bool = Depends(verify_admin_password)):
    """Upload a new data file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")

    # Prevent path traversal
    if '..' in file.filename or '/' in file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        content = await file.read()
        # Validate JSON
        json.loads(content.decode('utf-8'))

        filepath = DATA_DIR / file.filename
        with open(filepath, 'wb') as f:
            f.write(content)

        return {"status": "uploaded", "name": file.filename}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.delete("/api/admin/data-files/{filename}")
async def delete_data_file(filename: str, authorized: bool = Depends(verify_admin_password)):
    """Delete a specific data file."""
    # Prevent path traversal
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Prevent deletion of critical files
    protected_files = {'topics_tasks.json', 'consent.json', 'llm_config.json', 'personas.json'}
    if filename in protected_files:
        raise HTTPException(status_code=403, detail="Cannot delete protected system files")

    filepath = DATA_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        filepath.unlink()
        return {"status": "deleted", "name": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


# ==================== Conversations API ====================

@app.get("/api/admin/conversations")
async def list_conversations(authorized: bool = Depends(verify_admin_password)):
    """List all conversation files."""
    conversations = []
    if CONVERSATIONS_DIR.exists():
        for f in CONVERSATIONS_DIR.iterdir():
            if f.is_file() and f.suffix == '.json':
                stat = f.stat()
                # Try to read basic info
                try:
                    with open(f, 'r') as file:
                        data = json.load(file)
                        conversations.append({
                            "session_id": f.stem,
                            "filename": f.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "topic": data.get("topic", "Unknown"),
                            "message_count": len(data.get("messages", [])),
                            "started_at": data.get("started_at"),
                            "ended_at": data.get("ended_at")
                        })
                except:
                    conversations.append({
                        "session_id": f.stem,
                        "filename": f.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "topic": "Unknown",
                        "message_count": 0,
                        "started_at": None,
                        "ended_at": None
                    })
    return sorted(conversations, key=lambda x: x["modified"], reverse=True)


@app.get("/api/admin/conversations/{session_id}")
async def get_conversation(session_id: str, authorized: bool = Depends(verify_admin_password)):
    """Get content of a specific conversation."""
    # Prevent path traversal
    if '..' in session_id or '/' in session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    filepath = CONVERSATIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        with open(filepath, 'r') as f:
            content = json.load(f)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read conversation: {str(e)}")


@app.get("/api/admin/conversations/{session_id}/download")
async def download_conversation(session_id: str, authorized: bool = Depends(verify_admin_password)):
    """Download a specific conversation file."""
    # Prevent path traversal
    if '..' in session_id or '/' in session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    filepath = CONVERSATIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    return FileResponse(
        path=str(filepath),
        filename=f"{session_id}.json",
        media_type='application/json'
    )


@app.delete("/api/admin/conversations/{session_id}")
async def delete_conversation(session_id: str, authorized: bool = Depends(verify_admin_password)):
    """Delete a specific conversation."""
    # Prevent path traversal
    if '..' in session_id or '/' in session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    filepath = CONVERSATIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        filepath.unlink()
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


@app.get("/api/admin/conversations-download-all")
async def download_all_conversations(authorized: bool = Depends(verify_admin_password)):
    """Download all conversations as a ZIP file."""
    if not CONVERSATIONS_DIR.exists():
        raise HTTPException(status_code=404, detail="No conversations directory found")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for f in CONVERSATIONS_DIR.iterdir():
            if f.is_file() and f.suffix == '.json':
                zip_file.write(f, f.name)

    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="conversations_{timestamp}.zip"'
        }
    )


@app.delete("/api/admin/conversations-delete-all")
async def delete_all_conversations(authorized: bool = Depends(verify_admin_password)):
    """Delete all conversations."""
    if not CONVERSATIONS_DIR.exists():
        return {"status": "success", "deleted_count": 0}

    deleted_count = 0
    errors = []

    for f in CONVERSATIONS_DIR.iterdir():
        if f.is_file() and f.suffix == '.json':
            try:
                f.unlink()
                deleted_count += 1
            except Exception as e:
                errors.append(f"{f.name}: {str(e)}")

    if errors:
        return {
            "status": "partial",
            "deleted_count": deleted_count,
            "errors": errors
        }

    return {"status": "success", "deleted_count": deleted_count}
