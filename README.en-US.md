[English](README.en-US.md) | [中文](README.md)

## What This App Does

Video Dubbing API is an asynchronous service for turning source video or audio into translated dubbing outputs. It packages the full workflow behind HTTP APIs, including transcription, translation, subtitle generation, text-to-speech, vocal separation, audio replacement, and final media export.

Typical use cases:

- Submit a video or audio file for automatic dubbing.
- Track long-running processing progress by `task_id`.
- Download generated subtitles and output media files after the pipeline completes.

## Screenshots

![Application screenshot 1](screenshot/image1.png)

![Application screenshot 2](screenshot/image2.png)

TIPS: UI project is [→Here←](https://github.com/NicolasFive/Video_Add_Dubbing_UI)

# Quick Start

## 1. Prerequisites

- Python `3.12.3+`
- Redis `6+` (or Docker)
- FFmpeg available in `PATH`
- A virtual environment is recommended

## 2. Environment Variables

Create a `.env` file in the project root. The table below describes each configuration item.

| Key | Required | Type | Example | Description |
| --- | --- | --- | --- | --- |
| `APP_NAME` | No | string | `Video Dubbing API` | Application display name. |
| `DEBUG` | No | boolean | `False` | Enables debug mode when set to `True`. |
| `LOG_LEVEL` | No | string | `INFO` | Logging level (for example `DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `SERVER_HOST` | No | string | `0.0.0.0` | API bind host. |
| `SERVER_PORT` | No | integer | `8000` | API bind port. |
| `STORAGE_ROOT` | No | string | `./storage` | Root directory for persistent and temp files. |
| `UPLOAD_DIR` | No | string | `uploads` | Subdirectory for uploaded source videos. |
| `TEMP_DIR` | No | string | `temp` | Subdirectory for intermediate processing files. |
| `RESULT_DIR` | No | string | `results` | Subdirectory for final outputs. |
| `ASSEMBLYAI_KEY` | Yes | string | `your_assemblyai_key` | API key for AssemblyAI transcription service. |
| `OPENAI_API_KEY` | Yes | string | `your_openai_api_key` | API key for OpenAI-compatible translation/reduction service. |
| `OPENAI_BASE_URL` | No | string(URL) | `https://api.openai.com/v1` | Base URL for OpenAI-compatible API endpoint. |
| `VOLCANO_TTS_APPID` | Yes | string | `your_volcano_app_id` | Doubao TTS 1.0 app ID. |
| `VOLCANO_TTS_ACCESS_TOKEN` | Yes | string | `your_volcano_access_token` | Doubao TTS 1.0 access token. |
| `REDIS_URL` | Yes | string(URL) | `redis://127.0.0.1:6379/0` | Redis connection URL used for task status storage. |
| `CELERY_BROKER_URL` | Yes | string(URL) | `redis://127.0.0.1:6379/0` | Celery broker/backend URL. |
| `FFMPEG_BIN` | No | string | `ffmpeg` | FFmpeg executable name or absolute path. |
| `DEMUCS_MODEL` | No | string | `htdemucs` | Demucs model identifier for vocal separation. | 3

Example `.env`:

```env
APP_NAME=Video Dubbing API
DEBUG=False
LOG_LEVEL=INFO
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

STORAGE_ROOT=./storage
UPLOAD_DIR=uploads
TEMP_DIR=temp
RESULT_DIR=results

ASSEMBLYAI_KEY=your_assemblyai_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

VOLCANO_TTS_APPID=your_volcano_app_id
VOLCANO_TTS_ACCESS_TOKEN=your_volcano_access_token

REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0

FFMPEG_BIN=ffmpeg
DEMUCS_MODEL=htdemucs
```

## 3. Quick Start Method A: Local Commands

### 3.1 Install Dependencies

```bash
python -m venv venv
# Linux/macOS: source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -e .
```

### 3.2 Start API

```bash
python ./app/main.py
```

### 3.3 Start Celery Worker (new terminal)

Linux/macOS:

```bash
celery -A app.tasks.backend worker -l info
```

Windows (recommended):

```powershell
celery -A app.tasks.backend worker -l info --pool=solo
```

Note: Ensure Redis is already running and reachable by `REDIS_URL`/`CELERY_BROKER_URL`.

## 4. Quick Start Method B: Docker

```bash
docker compose up --build
```

Access URLs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/v1/health`

Notes:

- Current `docker-compose.yml` starts `api` and `redis`.
- Inside the `api` container, `scripts/start.sh` starts both API and Celery worker.

## 5. HTTP API Details

Base URL (local default): `http://127.0.0.1:8000`

### 5.1 `POST /v1/dubbing`

Purpose: Submit an asynchronous dubbing task and return `task_id`.

Content-Type: `multipart/form-data`

#### Request Parameters

| Name | In | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `video` | form-data | file | conditional | Uploaded source video file. |
| `audio` | form-data | file | conditional | Uploaded source audio file (audio-only dubbing flow). |
| `voice_types` | form-data | array[string] | No | Multi-speaker voice types. Submit multiple values by repeating fields (for example `-F "voice_types=a" -F "voice_types=b"`). |
| `line_type` | form-data | string | No | Pipeline config type. Defaults to `default` when omitted. |
| `task_id` | form-data | string | No | Task ID. Auto-generated if omitted. Can be reused for resume/retry workflows. |
| `start_step` | form-data | string | No | Start from a specific pipeline step (exact step name required). |
| `end_step` | form-data | string | No | Stop after a specific pipeline step. |
| `duck_db` | form-data | integer | No | Background music ducking volume parameter. |

Validation rules:

- For a new task (when `task_id` is omitted), at least one of `video` or `audio` must be provided.
- When `task_id` is provided (resume/retry), API allows submitting without new upload files.

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Unique task ID. |
| `status` | string | Initial status, usually `pending`. |
| `message` | string | Result message. |
| `created_at` | string(datetime) | Task creation timestamp. |

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/v1/dubbing" \
  -F "video=@./sample.mp4" \
  -F "voice_types=zh_female_xiaohe_uranus_bigtts" \
  -F "voice_types=zh_male_wennuanahu_moon_bigtts"
```

### 5.2 `GET /v1/status/{task_id}`

Purpose: Query task status and progress.

#### Path Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `task_id` | string | Yes | Task ID. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `status` | string | `pending` / `processing` / `success` / `failed` / `unknown`. |
| `video_url` | string/null | Output video URL/path (may be empty in current implementation). |
| `subtitle_url` | string/null | Output subtitle URL/path (may be empty in current implementation). |
| `error_detail` | string/null | Error details (may be returned when failed). |
| `progress` | integer | Progress percentage in range `0-100`. |
| `current_step` | string/null | Current pipeline step name (defaults to `Unknown` if status detail is missing). |

Example request:

```bash
curl "http://127.0.0.1:8000/v1/status/<task_id>"
```

Example response:

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "processing",
  "video_url": null,
  "subtitle_url": null,
  "error_detail": null,
  "progress": 40,
  "current_step": "Translating"
}
```

### 5.3 `GET /v1/result/{task_id}`

Purpose: List task-generated files and provide downloadable links.

#### Path Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `task_id` | string | Yes | Task ID. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `status` | string | `pending` / `processing` / `success` / `failed` / `unknown`. |
| `files` | array | Generated file list under `storage/temp/{task_id}`. |
| `files[].file_name` | string | File name. |
| `files[].relative_path` | string | Task-relative file path (POSIX style). |
| `files[].size_bytes` | integer | File size in bytes. |
| `files[].updated_at` | string(datetime) | Last modified time. |
| `files[].download_url` | string | Download endpoint for this file. |
| `progress` | integer | Progress percentage in range `0-100`. |
| `current_step` | string/null | Current pipeline step. |
| `error_detail` | string/null | Error details when failed. |

Note: current implementation returns `files[].download_url` in the form `/v1/result/task_id/{task_id}/download?file=...`; clients should prefer using the returned URL directly.

Example request:

```bash
curl "http://127.0.0.1:8000/v1/result/<task_id>"
```

Example response:

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "success",
  "files": [
    {
      "file_name": "final_video_path.mp4",
      "relative_path": "final_video_path.mp4",
      "size_bytes": 27834567,
      "updated_at": "2026-03-13T11:32:10",
      "download_url": "/v1/result/task_id/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/download?file=final_video_path.mp4"
    },
    {
      "file_name": "subtitles.srt",
      "relative_path": "subtitles.srt",
      "size_bytes": 9210,
      "updated_at": "2026-03-13T11:31:20",
      "download_url": "/v1/result/task_id/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/download?file=subtitles.srt"
    }
  ],
  "progress": 100,
  "current_step": "Completed",
  "error_detail": null
}
```

### 5.4 `GET /v1/result/{task_id}/download`

Purpose: Download a generated file by task-relative path.

#### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | string | Yes | File relative path returned by `files[].relative_path`. |

#### Success Response (`200`)

- Binary stream response (with `Content-Disposition` download filename).

Example request:

```bash
curl -L "http://127.0.0.1:8000/v1/result/<task_id>/download?file=subtitles.srt" -o subtitles.srt
```

### 5.5 `GET /v1/pipline/config`

Purpose: Get stage config list for the specified `line_type`.

#### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `line_type` | string | No | Config type (for example `default` or `doubao_v1`). Uses `default` when omitted. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `stages` | array | Stage list under the selected line_type. |
| `stages[].key` | string | Stage unique key. |
| `stages[].name` | string | Stage display name. |

Example request:

```bash
curl "http://127.0.0.1:8000/v1/pipline/config"
curl "http://127.0.0.1:8000/v1/pipline/config?line_type=doubao_v1"
```

### 5.6 `GET /v1/pipline/line-types`

Purpose: List all available line types.

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `line_types` | array[string] | All available line types. |

Example request:

```bash
curl "http://127.0.0.1:8000/v1/pipline/line-types"
```

### 5.7 `GET /v1/optimize/{task_id}`

Purpose: Read stage data for a task (loads `context.pkl` and calls stage `get_data`).

#### Path Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `task_id` | string | Yes | Task ID. |

#### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `stage` | string | Yes | Stage key/name (for example `Translating` / `translate`). |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `stage` | string | Normalized stage key. |
| `data` | string | Stage data (JSON string when data is structured). |

### 5.8 `POST /v1/optimize/{task_id}`

Purpose: Update stage data for a task (calls stage `set_data` and writes back `context.pkl`).

Content-Type: `multipart/form-data`

#### Request Parameters

| Name | In | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `stage` | form-data | string | Yes | Stage key/name (for example `Translating` / `translate`). |
| `data` | form-data | string | Yes | Stage payload. Parsed as JSON first; raw string is used if JSON parse fails. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `stage` | string | Normalized stage key. |
| `message` | string | Update result message. |

### 5.9 `GET /v1/optimize/self_check/{task_id}`

Purpose: Run stage-level `self_check` logic.

#### Path Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `task_id` | string | Yes | Task ID. |

#### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `stage` | string | Yes | Stage key/name. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `stage` | string | Normalized stage key. |
| `data` | array[SelfCheckItem] | Self-check result list. |
| `data[].index` | integer | Check item index. |
| `data[].check_point` | string | Check point name. |
| `data[].issue` | string/null | Detected issue description. |
| `data[].warning_content` | string/null | Content that needs attention. |
| `data[].confirm_content` | string/null | Suggested confirmed or corrected content. |

Example request:

```bash
curl "http://127.0.0.1:8000/v1/optimize/self_check/<task_id>?stage=Translating"
```

Example response:

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "stage": "Translating",
  "data": [
    {
      "index": 0,
      "check_point": "terminology",
      "issue": "Brand name translation is inconsistent",
      "warning_content": "OpenAI was translated differently across lines",
      "confirm_content": "Use the same translated term for all occurrences"
    }
  ]
}
```

### 5.10 `POST /v1/optimize/check_confirm/{task_id}`

Purpose: Submit confirmation payload and run stage-level `check_confirm` logic.

Content-Type: `multipart/form-data`

#### Request Parameters

| Name | In | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `stage` | form-data | string | Yes | Stage key/name. |
| `data` | form-data | string(JSON) | Yes | Must be a JSON array. Each element is parsed into a `SelfCheckItem`. |

Each `SelfCheckItem` in `data` supports these fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `index` | integer | Yes | Check item index. |
| `check_point` | string | Yes | Check point name. |
| `issue` | string/null | No | Issue description. |
| `warning_content` | string/null | No | Content needing attention. |
| `confirm_content` | string/null | No | User-confirmed content. |

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `task_id` | string | Task ID. |
| `stage` | string | Normalized stage key. |

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/v1/optimize/check_confirm/<task_id>" \
  -F "stage=Translating" \
  -F 'data=[{"index":0,"check_point":"terminology","issue":"Brand name translation is inconsistent","warning_content":"OpenAI was translated differently across lines","confirm_content":"Use one consistent translation"}]'
```

Example response:

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "stage": "Translating"
}
```

Error notes:

- The endpoint returns `400` when `data` is not valid JSON.
- If any item in `data` cannot be parsed into `SelfCheckItem`, validation fails.

### 5.11 `GET /v1/health`

Purpose: Health check for API and dependency components.

#### Request Parameters

None.

#### Success Response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `status` | string | `healthy` / `degraded` / `unhealthy`. |
| `details.redis` | string | Redis status. |
| `details.ffmpeg` | string | FFmpeg status. |
| `details.demucs` | string | Demucs status. |
| `details.disk_usage_percent` | number | Disk usage percentage. |

Example request:

```bash
curl "http://127.0.0.1:8000/v1/health"
```

## 6. Common Problems

- `Failed to connect to Redis`: check `REDIS_URL` and Redis port.
- `ffmpeg missing`: install FFmpeg and verify `ffmpeg -version` works.
- Worker receives tasks but no progress updates: check Celery logs and broker settings in `.env`.
- Worker multiprocessing issues on Windows: use `--pool=solo`.
