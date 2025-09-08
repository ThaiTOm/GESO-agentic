import os
import uuid
import whisper
import torchaudio as ta
import json
import shutil  # <<< NEW >>>
from datetime import datetime  # <<< NEW >>>
from chatterbox.tts import ChatterboxTTS
import aiofiles
from fastapi import (
    APIRouter, HTTPException, FastAPI, UploadFile, File, Form, BackgroundTasks
)
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from fastapi.concurrency import run_in_threadpool
from starlette.staticfiles import StaticFiles

from config import settings
from graph.speaking_graph import build_ielts_graph, IeltsState

os.environ["LANGSMITH_TRACING_V2"] = settings.LANGSMITH_TRACING_V2
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.SPEAKING_PROJECT


# --- Pydantic Models for API Request & Response ---

class IeltsTurnResponse(BaseModel):
    """The response sent back to the client after each turn."""
    examiner_audio_url: str = Field(description="URL to the generated audio file for the examiner's question/response.")
    examiner_text: str = Field(description="The text version of the examiner's response.")
    current_state: Dict[str, Any] = Field(
        description="The full, updated state of the test to be sent back in the next request.")


# --- Global Objects and Configuration ---
router = APIRouter()
app = FastAPI(title="IELTS Speaking Practice API", version="1.0.0")

# Create directories if they don't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
# <<< NEW >>> Directory for permanent logs
LOG_DIR = "conversation_logs"
os.makedirs(LOG_DIR, exist_ok=True)


# --- Model Loading ---
print("Loading Whisper model...")
stt_model = whisper.load_model("base", device="cuda")
print("Whisper model loaded.")

print("Loading TTS model...")
tts_model = ChatterboxTTS.from_pretrained(device="cuda")
print("TTS model loaded.")

# --- Graph Initialization ---
print("Building IELTS graph...")
ielts_graph = build_ielts_graph()
print("Graph built successfully.")


# --- <<< CHANGED/NEW >>> Helper Function for Archiving and Cleanup ---
def archive_and_cleanup_turn(
    turn_log_path: str,
    temp_input_path: Optional[str],
    temp_output_path: str,
    log_data: dict
):
    """
    Saves the input/output audio and a JSON metadata file to a permanent
    log directory, then cleans up the temporary files.
    """
    try:
        # 1. Create the unique directory for this turn if it doesn't exist
        os.makedirs(turn_log_path, exist_ok=True)

        # 2. Archive files by copying them to the log directory
        if temp_input_path and os.path.exists(temp_input_path):
            # The input file will be saved as 'input.wav' (or its original extension)
            input_filename = f"input{os.path.splitext(temp_input_path)[1]}"
            shutil.copy(temp_input_path, os.path.join(turn_log_path, input_filename))

        if os.path.exists(temp_output_path):
            # The output file will be saved as 'examiner_response.wav'
            shutil.copy(temp_output_path, os.path.join(turn_log_path, "examiner_response.wav"))

        # 3. Save all metadata to a JSON file
        json_log_path = os.path.join(turn_log_path, "data.json")
        with open(json_log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)

        print(f"Successfully archived turn to {turn_log_path}")

    except Exception as e:
        print(f"Error archiving turn data for {turn_log_path}: {e}")

    finally:
        # 4. Clean up the original temporary files from UPLOAD_DIR and OUTPUT_DIR
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
                print(f"Cleaned up temporary input file: {temp_input_path}")
            except Exception as e:
                print(f"Error cleaning up temp input file {temp_input_path}: {e}")

        if os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
                print(f"Cleaned up temporary output file: {temp_output_path}")
            except Exception as e:
                print(f"Error cleaning up temp output file {temp_output_path}: {e}")


# --- API Endpoint ---
@router.post("/ielts-turn", response_model=IeltsTurnResponse)
async def ielts_turn(
        background_tasks: BackgroundTasks,
        user_audio: Optional[Union[UploadFile, str]] = File(None,
                                                description="The user's spoken response. Prioritized over user_query."),
        user_query: Optional[str] = Form(None,
                                         description="The user's text response. Used if user_audio is not provided."),
        current_state_str: str = Form("{}",
                                      description="The JSON string of the current test state. Send an empty object '{}' to start a new test.")
):
    """
    Handles a single turn in the IELTS speaking test.

    Manages the state of the conversation, processes user input (audio or text),
    runs it through the conversational graph, and returns the examiner's response.
    It also archives the interaction (audio and text) in the background.
    """
    # <<< NEW >>> Generate a unique ID for this entire turn/request
    turn_id = str(uuid.uuid4())
    turn_log_path = os.path.join(LOG_DIR, turn_id)

    # --- 1. Process and Validate the Incoming State ---
    try:
        parsed_state = json.loads(current_state_str)
        if "current_state" in parsed_state and isinstance(parsed_state.get("current_state"), dict):
            print("--- INFO: Unwrapping nested state from client request. ---")
            current_state = parsed_state["current_state"]
        else:
            current_state = parsed_state
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in current_state_str.")

    # <<< NEW >>> Keep a copy of the initial state for logging
    initial_state_for_logging = current_state.copy()

    user_response_text = ""
    input_filepath = None

    # --- 2. Handle User Input (Audio has priority) ---
    if user_audio and isinstance(user_audio, UploadFile) and user_audio.filename:
        # Use turn_id for clearer temporary file naming
        input_filename = f"{turn_id}{os.path.splitext(user_audio.filename)[1] or '.wav'}"
        input_filepath = os.path.join(settings.UPLOAD_DIR, input_filename)

        try:
            async with aiofiles.open(input_filepath, 'wb') as out_file:
                content = await user_audio.read()
                await out_file.write(content)

            transcribe_result = await run_in_threadpool(stt_model.transcribe, input_filepath)
            user_response_text = transcribe_result["text"]
            print(f"User transcription from audio: {user_response_text}")

        except Exception as e:
            # Clean up immediately on failure if file was created
            if input_filepath and os.path.exists(input_filepath):
                os.remove(input_filepath)
            raise HTTPException(status_code=500, detail=f"Error processing audio file: {e}")

    if not user_response_text and user_query:
        user_response_text = user_query
        print(f"User response from text query: {user_response_text}")

    # --- 3. Run the Conversational Graph ---
    current_state["user_response"] = user_response_text

    try:
        final_state = await ielts_graph.ainvoke(current_state)
    except Exception as e:
        if input_filepath and os.path.exists(input_filepath):
            os.remove(input_filepath)
        print(f"ERROR running graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing the test logic: {e}")

    examiner_response_text = final_state.get("examiner_question", "An error occurred.")
    print(f"Examiner response: {examiner_response_text}")

    # --- 4. Generate Examiner's Audio (Text-to-Speech) ---
    # Use turn_id for clearer temporary file naming
    output_filename = f"{turn_id}.wav"
    output_filepath = os.path.join(settings.OUTPUT_DIR, output_filename)

    try:
        wav_tensor = await run_in_threadpool(tts_model.generate, examiner_response_text)
        await run_in_threadpool(ta.save, output_filepath, wav_tensor, 24000)
    except Exception as e:
        if input_filepath and os.path.exists(input_filepath):
            os.remove(input_filepath)
        raise HTTPException(status_code=500, detail=f"TTS generation error: {e}")


    # --- <<< CHANGED >>> 5. Schedule Archiving and Cleanup ---
    # Prepare all data that needs to be logged
    log_data = {
        "turn_id": turn_id,
        "timestamp_utc": datetime.utcnow().isoformat(),
        "user_input_text": user_response_text,
        "examiner_output_text": examiner_response_text,
        "initial_state": initial_state_for_logging,
        "final_state": final_state
    }

    # Schedule the new function to run in the background
    # background_tasks.add_task(
    #     archive_and_cleanup_turn,
    #     turn_log_path=turn_log_path,
    #     temp_input_path=input_filepath,
    #     temp_output_path=output_filepath,
    #     log_data=log_data
    # )

    # --- 6. Return the Final Response ---
    base_url = "http://ai.tvssolutions.vn:2110" # Replace with your actual domain/IP
    audio_url = f"{base_url}/{output_filepath[2:]}"

    return JSONResponse(content={
        "examiner_audio_url": audio_url,
        "examiner_text": examiner_response_text,
        "current_state": final_state
    })


# --- FastAPI App Configuration ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")
app.include_router(router, prefix="/api/v1", tags=["IELTS Speaking"])