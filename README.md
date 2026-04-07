[English](README.en-US.md) | [中文](README.md)

## 应用用途

Video Dubbing API 是一个用于将源视频或音频转换为译制配音结果的异步服务。它通过 HTTP API 封装了整条处理流水线，包括语音转写、文本翻译、字幕生成、语音合成、人声分离、音频替换以及最终媒体导出。

典型使用场景：

- 提交视频或音频文件，自动执行配音处理。
- 通过 `task_id` 跟踪长耗时任务的处理进度。
- 在处理完成后下载生成的字幕和输出媒体文件。

[看一下效果视频（bilibili）](https://www.bilibili.com/video/BV15gwJzNEqT/?vd_source=6d331a0e955c0b5b6e5f736db012b39e)

## UI截图

![应用截图 1](screenshot/image1.png)

![应用截图 2](screenshot/image2.png)

提示：UI 项目在 [→这里←](https://github.com/NicolasFive/Video_Add_Dubbing_UI)



# 快速开始

## 1. 前置要求

- Python `3.12.3+`
- Redis `6+`（或 Docker）
- FFmpeg 已加入 `PATH`
- 建议使用虚拟环境

## 2. 环境变量

在项目根目录创建 `.env` 文件，下表说明各配置项。

| Key | 必填 | 类型 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| `APP_NAME` | 否 | string | `Video Dubbing API` | 应用显示名称。 |
| `DEBUG` | 否 | boolean | `False` | 设为 `True` 时启用调试模式。 |
| `LOG_LEVEL` | 否 | string | `INFO` | 日志级别（例如 `DEBUG`、`INFO`、`WARNING`、`ERROR`）。 |
| `SERVER_HOST` | 否 | string | `0.0.0.0` | API 绑定主机。 |
| `SERVER_PORT` | 否 | integer | `8000` | API 绑定端口。 |
| `STORAGE_ROOT` | 否 | string | `./storage` | 持久化与临时文件的根目录。 |
| `UPLOAD_DIR` | 否 | string | `uploads` | 上传源视频子目录。 |
| `TEMP_DIR` | 否 | string | `temp` | 处理中间文件子目录。 |
| `RESULT_DIR` | 否 | string | `results` | 最终结果文件子目录。 |
| `ASSEMBLYAI_KEY` | 是 | string | `your_assemblyai_key` | AssemblyAI 转写服务 API Key。 |
| `OPENAI_API_KEY` | 是 | string | `your_openai_api_key` | OpenAI 兼容翻译/压缩服务 API Key。 |
| `OPENAI_BASE_URL` | 否 | string(URL) | `https://api.openai.com/v1` | OpenAI 兼容 API 端点基础 URL。 |
| `VOLCANO_TTS_APPID` | 是 | string | `your_volcano_app_id` | 豆包语音合成大模型1.0 App ID。 |
| `VOLCANO_TTS_ACCESS_TOKEN` | 是 | string | `your_volcano_access_token` | 豆包语音合成大模型1.0 Access Token。 |
| `REDIS_URL` | 是 | string(URL) | `redis://127.0.0.1:6379/0` | Redis 连接 URL，用于任务状态存储。 |
| `CELERY_BROKER_URL` | 是 | string(URL) | `redis://127.0.0.1:6379/0` | Celery broker/backend URL。 |
| `FFMPEG_BIN` | 否 | string | `ffmpeg` | FFmpeg 可执行名或绝对路径。 |
| `DEMUCS_MODEL` | 否 | string | `htdemucs` | 用于人声分离的 Demucs 模型标识。 |

`.env` 示例：

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

## 3. 快速启动方式 A：本地命令

### 3.1 安装依赖

```bash
python -m venv venv
# Linux/macOS: source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -e .
```

### 3.2 启动 API

```bash
python ./app/main.py
```

### 3.3 启动 Celery Worker（新终端）

Linux/macOS：

```bash
celery -A app.tasks.backend worker -l info
```

Windows（推荐）：

```powershell
celery -A app.tasks.backend worker -l info --pool=solo
```

说明：请确保 Redis 已启动，且 `REDIS_URL`/`CELERY_BROKER_URL` 可访问。

## 4. 快速启动方式 B：Docker

```bash
docker compose up --build
```

访问地址：

- Swagger UI: `http://127.0.0.1:8000/docs`
- 健康检查: `http://127.0.0.1:8000/v1/health`

说明：

- 当前 `docker-compose.yml` 会启动 `api` 与 `redis`。
- `api` 容器内由 `scripts/start.sh` 同时启动 API 与 Celery worker。

## 5. HTTP API 说明

基础 URL（本地默认）：`http://127.0.0.1:8000`

### 5.1 `POST /v1/dubbing`

用途：提交异步配音任务并返回 `task_id`。

Content-Type：`multipart/form-data`

#### 请求参数

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `video` | form-data | file | 条件必填 | 上传源视频文件。 |
| `audio` | form-data | file | 条件必填 | 上传源音频文件（纯音频配音流程）。 |
| `voice_types` | form-data | array[string] | 否 | 多说话人音色列表。可通过重复字段提交多个值（例如 `-F "voice_types=a" -F "voice_types=b"`）。 |
| `line_type` | form-data | string | 否 | 配置类型；不传时默认 `default`。 |
| `task_id` | form-data | string | 否 | 任务 ID；不传则自动生成。可用于断点续跑/重试。 |
| `start_step` | form-data | string | 否 | 从指定流程步骤开始（需填写精确步骤名）。 |
| `end_step` | form-data | string | 否 | 在指定流程步骤结束。 |
| `duck_db` | form-data | integer | 否 | 背景音乐 ducking 音量参数。 |

校验规则：

- 新任务（未提供 `task_id`）时，`video` 与 `audio` 至少提供一个。
- 提供 `task_id`（续跑/重试）时，允许不上传新文件。

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 唯一任务 ID。 |
| `status` | string | 初始状态，通常为 `pending`。 |
| `message` | string | 结果消息。 |
| `created_at` | string(datetime) | 任务创建时间戳。 |

请求示例：

```bash
curl -X POST "http://127.0.0.1:8000/v1/dubbing" \
  -F "video=@./sample.mp4" \
  -F "voice_types=zh_female_xiaohe_uranus_bigtts" \
  -F "voice_types=zh_male_wennuanahu_moon_bigtts"
```

### 5.2 `GET /v1/status/{task_id}`

用途：查询任务状态与进度。

#### 路径参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | string | 是 | 任务 ID。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `status` | string | `pending` / `processing` / `success` / `failed` / `unknown`。 |
| `video_url` | string/null | 输出视频 URL/路径（当前实现通常为空）。 |
| `subtitle_url` | string/null | 输出字幕 URL/路径（当前实现通常为空）。 |
| `error_detail` | string/null | 错误详情（失败时可能返回）。 |
| `progress` | integer | 进度百分比，范围 `0-100`。 |
| `current_step` | string/null | 当前流程步骤名（缺失时为 `Unknown`）。 |

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/status/<task_id>"
```

### 5.3 `GET /v1/result/list`

用途：递归扫描 `storage/temp` 目录及其子目录下的 `init.json` 文件，读取其中的 JSON 对象，并按文件最后修改时间倒序返回对象数组。

#### 查询参数

无。

#### 成功响应（`200`）

- JSON 数组。
- 数组中的每一项都是对应 `init.json` 文件里的 JSON 对象。
- 排序规则为 `init.json` 文件最后修改时间倒序。

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/result/list"
```

响应示例：

```json
[
  {
    "task_id": "579824cb-4277-483d-bb24-0ebcae9f81e3",
    "input_video_path": "storage\\temp\\579824cb-4277-483d-bb24-0ebcae9f81e3\\Chris finally wins something - QuahogTheater (1080p, h264).mp4",
    "input_audio_path": null,
    "work_dir": "storage\\temp\\579824cb-4277-483d-bb24-0ebcae9f81e3",
    "voice_source": null,
    "voice_types": [
      "zh_male_jingqiangkanye_emo_mars_bigtts"
    ],
    "line_type": "default",
    "duck_db": null,
    "no_cache": false,
    "update_time": "2026-04-07 10:26:24"
  }
]
```

说明：

- 当 `storage/temp` 不存在时，接口返回空数组 `[]`。
- 当某个 `init.json` 不是合法 JSON，或其根节点不是 JSON 对象时，接口返回 `500`。

### 5.4 `GET /v1/result/{task_id}`

用途：按任务查询已生成文件列表，并返回对应下载链接。

#### 路径参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | string | 是 | 任务 ID。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `status` | string | `pending` / `processing` / `success` / `failed` / `unknown`。 |
| `files` | array | `storage/temp/{task_id}` 下的生成文件列表。 |
| `files[].file_name` | string | 文件名。 |
| `files[].relative_path` | string | 相对任务目录路径（POSIX 风格）。 |
| `files[].size_bytes` | integer | 文件大小（字节）。 |
| `files[].updated_at` | string(datetime) | 最后修改时间。 |
| `files[].download_url` | string | 对应文件下载接口地址。 |
| `progress` | integer | 进度百分比，范围 `0-100`。 |
| `current_step` | string/null | 当前流程步骤。 |
| `error_detail` | string/null | 失败时的错误详情。 |

说明：当前实现返回的 `files[].download_url` 形如 `/v1/result/task_id/{task_id}/download?file=...`，客户端建议直接使用返回值。

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/result/<task_id>"
```

### 5.5 `GET /v1/result/{task_id}/download`

用途：根据任务内相对路径下载指定产物文件。

#### 查询参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | string | 是 | 来自 `files[].relative_path` 的相对路径。 |

#### 成功响应（`200`）

- 二进制流响应（带 `Content-Disposition` 下载文件名）。

请求示例：

```bash
curl -L "http://127.0.0.1:8000/v1/result/<task_id>/download?file=subtitles.srt" -o subtitles.srt
```

### 5.6 `GET /v1/pipline/config`

用途：获取指定 `line_type` 对应的 pipeline 阶段配置列表。

#### 查询参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `line_type` | string | 否 | 配置类型（如 `default` 或 `doubao_v1`）。不传则使用默认值 `default`。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `stages` | array | 对应 line_type 的流程阶段列表。 |
| `stages[].key` | string | 阶段唯一标识。 |
| `stages[].name` | string | 阶段显示名称。 |

请求示例：

```bash
# 获取默认配置
curl "http://127.0.0.1:8000/v1/pipline/config"

# 获取指定配置类型
curl "http://127.0.0.1:8000/v1/pipline/config?line_type=doubao_v1"
```

### 5.6 `GET /v1/pipline/line-types`

用途：查询所有可用的配置类型（line_type）。

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `line_types` | array[string] | 所有可用的配置类型列表。 |

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/pipline/line-types"
```

### 5.7 `GET /v1/optimize/{task_id}`

用途：读取指定任务某个流程阶段的数据（从 `context.pkl` 加载上下文后调用对应 stage 的 `get_data`）。

#### 路径参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | string | 是 | 任务 ID。 |

#### 查询参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `stage` | string | 是 | 流程阶段名或 key（例如 `Translating` / `translate`）。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `stage` | string | 标准化后的阶段名。 |
| `data` | string | 阶段数据（若为结构化数据，会序列化为 JSON 字符串）。 |

### 5.8 `POST /v1/optimize/{task_id}`

用途：修改指定任务某个流程阶段的数据（调用 stage 的 `set_data` 并回写 `context.pkl`）。

Content-Type：`multipart/form-data`

#### 请求参数

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `stage` | form-data | string | 是 | 流程阶段名或 key（例如 `Translating` / `translate`）。 |
| `data` | form-data | string | 是 | 阶段数据；优先按 JSON 解析，失败则按普通字符串处理。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `stage` | string | 标准化后的阶段名。 |
| `message` | string | 更新结果消息。 |

### 5.9 `GET /v1/optimize/self_check/{task_id}`

用途：执行指定 stage 的 `self_check` 逻辑。

#### 路径参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | string | 是 | 任务 ID。 |

#### 查询参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `stage` | string | 是 | 流程阶段名或 key。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `stage` | string | 标准化后的阶段名。 |
| `data` | array[SelfCheckItem] | 自检结果列表。 |
| `data[].index` | integer | 检查项序号。 |
| `data[].check_point` | string | 检查点名称。 |
| `data[].issue` | string/null | 发现的问题说明。 |
| `data[].warning_content` | string/null | 需要关注的内容。 |
| `data[].confirm_content` | string/null | 建议确认或修正后的内容。 |

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/optimize/self_check/<task_id>?stage=Translating"
```

响应示例：

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

用途：提交确认数据并执行指定 stage 的 `check_confirm` 逻辑。

Content-Type：`multipart/form-data`

#### 请求参数

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `stage` | form-data | string | 是 | 流程阶段名或 key。 |
| `data` | form-data | string(JSON) | 是 | 必须为 JSON 数组，每个元素都会解析为 `SelfCheckItem`。 |

`data` 中每个 `SelfCheckItem` 支持以下字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `index` | integer | 是 | 检查项序号。 |
| `check_point` | string | 是 | 检查点名称。 |
| `issue` | string/null | 否 | 问题描述。 |
| `warning_content` | string/null | 否 | 需要关注的内容。 |
| `confirm_content` | string/null | 否 | 用户确认后的内容。 |

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID。 |
| `stage` | string | 标准化后的阶段名。 |

请求示例：

```bash
curl -X POST "http://127.0.0.1:8000/v1/optimize/check_confirm/<task_id>" \
  -F "stage=Translating" \
  -F 'data=[{"index":0,"check_point":"terminology","issue":"Brand name translation is inconsistent","warning_content":"OpenAI was translated differently across lines","confirm_content":"统一改为同一个译名"}]'
```

响应示例：

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "stage": "Translating"
}
```

错误说明：

- `data` 不是合法 JSON 时，接口返回 `400`。
- `data` 中元素无法映射为 `SelfCheckItem` 时，接口会返回校验错误。

### 5.11 `GET /v1/health`

用途：API 与依赖组件健康检查。

#### 成功响应（`200`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | `healthy` / `degraded` / `unhealthy`。 |
| `details.redis` | string | Redis 状态。 |
| `details.ffmpeg` | string | FFmpeg 状态。 |
| `details.demucs` | string | Demucs 状态。 |
| `details.disk_usage_percent` | number | 磁盘占用百分比。 |

请求示例：

```bash
curl "http://127.0.0.1:8000/v1/health"
```

## 6. 常见问题

- `Failed to connect to Redis`：检查 `REDIS_URL` 与 Redis 端口。
- `ffmpeg missing`：安装 FFmpeg，并确认 `ffmpeg -version` 可执行。
- Worker 能收到任务但无进度更新：检查 Celery 日志与 `.env` 中 broker 配置。
- Windows 下 Worker 多进程异常：使用 `--pool=solo`。
