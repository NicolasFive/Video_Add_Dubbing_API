# README For Developer

Developer-focused documentation for `video_dubbing_api`.

## 1. Tech Stack

- API: FastAPI
- Async queue: Celery
- Broker/backend: Redis
- Audio/video: FFmpeg, Demucs, Pydub, ffmpeg-python
- AI services: AssemblyAI, OpenAI-compatible LLM, Volcano TTS
- Packaging: `pyproject.toml` (`pip install -e .`)

## 2. Architecture Overview (Project Structure)

```text
video_dubbing_api/
|- .env                      # Environment variables (API keys, path configuration)
|- .gitignore
|- requirements.txt          # Or pyproject.toml
|- README.md
|- Dockerfile                # Includes ffmpeg, demucs, and Python runtime
|- docker-compose.yml        # Orchestrates API, Redis, Worker (if async queue is needed)
|
|- app/                      # Core source code
|  |- __init__.py
|  |- main.py                # FastAPI entry, only responsible for route registration and middleware
|  |
|  |- api/                   # Interface layer (Controllers)
|  |  |- __init__.py
|  |  |- v1/
|  |  |  |- __init__.py
|  |  |  |- router.py        # Aggregates all v1 routes
|  |  |  |- endpoints/
|  |  |     |- dubbing.py    # POST /dubbing (submit task)
|  |  |     |- status.py     # GET /status/{task_id} (query progress)
|  |  |     |- health.py     # GET /health (health check)
|  |
|  |- core/                  # Core configuration
|  |  |- __init__.py
|  |  |- config.py           # Pydantic Settings for all configs
|  |  |- logging.py          # Unified logging setup
|  |  |- exceptions.py       # Custom exceptions (e.g., DemucsError, TTSError)
|  |  |- security.py         # Authentication and rate limiting
|  |  |- database.py         # Database connection
|  |
|  |- services/              # Business logic layer (core orchestration)
|  |  |- __init__.py
|  |  |- pipeline.py         # Master orchestrator for the full dubbing pipeline
|  |  |
|  |  |- audio/              # Audio processing sub-services
|  |  |  |- __init__.py
|  |  |  |- separator.py     # Wraps Demucs invocation
|  |  |  |- mixer.py         # Wraps audio mixing logic
|  |  |  |- replacer.py      # Wraps FFmpeg audio replacement
|  |  |
|  |  |- transcription/      # Transcription sub-service
|  |  |  |- __init__.py
|  |  |  |- assemblyai_client.py # Wraps AssemblyAI SDK
|  |  |
|  |  |- translation/        # Translation sub-service
|  |  |  |- __init__.py
|  |  |  |- llm_translator.py # Wraps LLM translation logic
|  |  |
|  |  |- subtitle/           # Subtitle sub-services
|  |  |  |- __init__.py
|  |  |  |- generator.py     # Generates .srt/.ass files
|  |  |  |- burner.py        # Wraps FFmpeg subtitle burn-in
|  |  |
|  |  |- timing/             # Timing service
|  |  |  |- __init__.py
|  |  |  |- speed_ratio.py   # Pre-checks subtitle speed ratio
|  |  |
|  |  |- tts/                # Text-to-speech sub-service
|  |     |- __init__.py
|  |     |- volcano_tts.py   # Wraps Volcano Engine TTS API
|  |
|  |- models/                # Data models
|  |  |- __init__.py
|  |  |- schemas.py          # API request/response Pydantic models
|  |  |- domain.py           # Internal domain objects (e.g., SubtitleLine, AudioSegment)
|  |
|  |- utils/                 # Shared utilities
|  |  |- __init__.py
|  |  |- file_manager.py     # Temp file creation, cleanup, directory management
|  |  |- cmd_runner.py       # Safely runs shell commands (demucs, ffmpeg)
|  |  |- time_utils.py       # Timestamp conversion (ms <-> HH:MM:SS)
|  |  |- redis_oper.py       # Encapsulates common Redis operations for service layer reuse
|  |
|  |- tasks/                 # Async tasks (strongly recommended)
|     |- __init__.py
|     |- worker.py           # Celery/Arq task definition (runs pipeline)
|     |- backend.py          # Task status backend config (Redis)
|
|- tests/                    # Tests
|  |- __init__.py
|  |- conftest.py            # Pytest fixtures (Mock FFmpeg, Mock APIs)
|  |- test_services/         # Step-level service tests
|  |- test_pipeline/         # End-to-end pipeline orchestration tests
|  |- test_api/              # API integration tests
|
|- storage/                  # Persistent storage (local in dev, cloud-mounted in prod)
|  |- uploads/               # User-uploaded original videos
|  |- temp/                  # Intermediate files (e.g., vocal separation outputs)
|  |- results/               # Final output videos
|
|- scripts/                  # Operations scripts
  |- start.sh               # Start services
  |- clean_temp.sh          # Periodic temp cleanup
```

## 3. Pipeline Steps

Defined in `app/services/pipeline.py`:

| Step | Progress | Purpose | AI Vendor |
| --- | --- | --- | --- |
| `Analyzing Video` | 5 | Read video dimensions and calculate subtitle font size. | N/A |
| `Separating Vocals` | 10 | Separate vocals and instrumentals from source audio. | Meta AI (Demucs) |
| `Transcribing` | 25 | Convert speech to timed text segments. | AssemblyAI |
| `Translating` | 40 | Translate transcript text to target language. | OpenAI-compatible LLM |
| `Building Subtitles Data` | 45 | Build subtitle objects and run speed-ratio based timing adjustments (gap extension and subtitle merge strategies). | N/A |
| `Synthesizing Voice` | 50 | Generate dubbing audio clips for each subtitle line. | Volcano Engine (ByteDance) |
| `Mixing Audio` | 60 | Overlay TTS clips on instrumental/background track. | N/A |
| `Replacing Audio` | 70 | Replace original video audio stream with mixed dubbing track. | N/A |
| `Generating Subtitles` | 80 | Produce subtitle file (`.srt`). | N/A |
| `Burning Subtitles` | 90 | Burn subtitles into the dubbed video. | N/A |
| `Completed` | 100 | Finalize output and mark task as completed. | N/A |

Progress is persisted into Redis with key format:

- `task:{task_id}`

Fields include:

- `status`
- `progress`
- `current_step`
- `updated_at`
- `error` (optional)

## 4. Local Development Setup

### 4.1 Install and run

```bash
python -m venv venv
# Linux/macOS: source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -e .
```

### 4.2 Run services

Terminal A:

```bash
python ./app/main.py
```

Terminal B:

```bash
celery -A app.tasks.backend worker -l info
```

Windows recommended worker command:

```powershell
celery -A app.tasks.backend worker -l info --pool=solo
```

## 5. Storage Layout

| Path | Type | Purpose |
| --- | --- | --- |
| `storage/` | directory | Root storage directory for runtime data. |
| `storage/temp/<task_id>/` | directory | Per-task intermediate workspace for processing artifacts. |
| `storage/temp/<task_id>/transcribe_log.json` | file | Raw transcription output log. |
| `storage/temp/<task_id>/translation_log.json` | file | Translation and reduction trace log. |
| `storage/temp/<task_id>/tts_*.wav` | file set | Per-segment synthesized TTS audio clips. |
| `storage/temp/<task_id>/mixed_audio.wav` | file | Final mixed audio track before replacing source audio. |
| `storage/temp/<task_id>/subtitles.srt` | file | Generated subtitle file used for burn-in. |
| `storage/temp/<task_id>/final_video_path.mp4` | file | Final dubbed video after audio replacement and subtitle burn-in. |
| `storage/temp/<task_id>/context.pkl` | file | Serialized pipeline context for resume/retry workflows. |

## 6. Troubleshooting

- Redis connection errors
  - verify `REDIS_URL` and Redis health
- Celery task not consumed
  - ensure worker is running with the same broker URL
- FFmpeg command not found
  - set `FFMPEG_BIN` or install FFmpeg in PATH
- Unexpected resume behavior
  - check `context.pkl` and `start_step` exact string match
- Long task timeout
  - review Celery `task_time_limit` and `task_soft_time_limit`

## 7. Contribution Notes

- Keep endpoint layer thin and move business logic to `services/`.
- Persist task progress through `app/utils/redis_oper.py`.
- Add tests under matching domain folder in `tests/`.
- Prefer extending pipeline steps with clear progress semantics.
