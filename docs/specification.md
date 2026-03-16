
# Beat Saber Auto Clip Tool

## Implementation Specification v1

### Overview

Create a Python CLI tool that automatically cuts Beat Saber gameplay clips from OBS recordings using event data stored in `DataRecorder`'s SQLite database.

The tool:

1. Reads play records from `MovieCutRecord` in `beatsaber.db`
2. Matches them to OBS recordings
3. Calculates clip start/end times
4. Cuts clips using ffmpeg
5. Names files using a configurable template
6. Optionally organizes files into directories

The tool is designed to be modular and testable.

---

# Runtime Environment

### Python

Python environment must not depend on system Python.

Use:

```
uv
```

Project must support:

```
uv sync
uv run bs-autocut config.toml
```

Target Python version:

```
Python 3.12
```

---

# External Dependencies

Only minimal dependencies should be used.

Allowed libraries:

```
standard library
sqlite3
pathlib
subprocess
datetime
dataclasses
tomllib
logging
typing
pytest (for tests)
```

Do not use heavy frameworks.

---

# Project Structure

```
bs_autocut/

pyproject.toml
config.toml

src/
  bs_autocut/
    __init__.py
    cli.py
    orchestrator.py

    config_loader.py
    models.py

    db/
        reader.py

    video/
        scanner.py
        metadata.py

    clip/
        planner.py
        ffmpeg_runner.py

    output/
        filename_builder.py
        path_builder.py

tests/
    test_filename_builder.py
    test_clip_planner.py
    test_video_matcher.py
```

---

# SQLite Database

Database file:

```
beatsaber.db
```

Only one table must be used:

```
MovieCutRecord
```

Do NOT read `NoteScore` (too large).

---

# SQL Query

Use the following query:

```sql
SELECT
    startTime,
    endTime,
    start,
    menuTime,
    songHash,
    songName,
    difficulty,
    rank,
    score,
    cleared
FROM MovieCutRecord
ORDER BY startTime;
```

---

# Data Models

All models must be defined in `models.py`.

### PlaySession

Represents one song play.

```
@dataclass(frozen=True)
class PlaySession:
    start_time: int
    end_time: int
    start: int | None
    menu_time: int | None

    song_hash: str
    song_name: str
    difficulty: str

    rank: str
    score: int
    cleared: str
```

---

### VideoFile

Represents one OBS recording.

```
@dataclass(frozen=True)
class VideoFile:
    path: Path
    start_time: float
    duration: float
```

---

### ClipPlan

Represents a clip to generate.

```
@dataclass(frozen=True)
class ClipPlan:
    video_path: Path

    start_sec: float
    end_sec: float

    output_path: Path

    session: PlaySession
```

---

# Configuration File

Configuration must be a single TOML file.

Example:

```toml
[paths]
db = "/path/to/beatsaber.db"
videos = "/path/to/obs/videos"
output = "/path/to/output"

[cut]
mode = "song"
pre_roll = 6.0
post_roll = 4.0

[video]
extensions = ["mkv", "mp4"]

[output]
format = "mp4"
filename_template = "{song} [{difficulty}] {rank} {score}"

[organize]
enabled = true
path_template = "{song}/{difficulty}"

[ffmpeg]
ffmpeg_bin = "ffmpeg"
ffprobe_bin = "ffprobe"
mode = "reencode"

video_codec = "libx264"
audio_codec = "aac"
crf = 18
preset = "fast"

extra_input_args = []
extra_output_args = []

[run]
dry_run = true
overwrite = false
```

---

# Clip Mode

Cut behavior must support three modes.

```
song
play
with_result
```

Rules:

| mode        | start     | end      |
| ----------- | --------- | -------- |
| song        | start     | endTime  |
| play        | startTime | endTime  |
| with_result | start     | menuTime |

---

# Unique Clip ID

Each clip must contain a unique identifier.

```
{startTime}_{songHash[:8]}
```

Example:

```
1710000123_abc12345
```

---

# Filename Generation

User defines:

```
filename_template
```

Example:

```
"{song} [{difficulty}] {rank}"
```

Final filename:

```
{filename_template}__{unique_id}.{ext}
```

Example:

```
Idol [ExpertPlus] SS__1710000123_abc12345.mp4
```

---

# Template Variables

Supported variables:

```
song
difficulty
rank
score
hash
start_time
date
time
```

Date/time are derived from startTime.

---

# Directory Organization

Optional directory structure using template.

Example:

```
path_template = "{song}/{difficulty}"
```

Output:

```
clips/
  Idol/
    ExpertPlus/
      Idol [ExpertPlus] SS__1710000123_abc12345.mp4
```

---

# Filename Sanitization

Invalid characters must be replaced.

```
/ \ : * ? " < > | → _
```

Whitespace trimmed.

Maximum length:

```
200 characters
```

Unique ID must always remain.

---

# Video Detection

Video files located in:

```
paths.videos
```

Allowed extensions defined in config.

Example:

```
mkv
mp4
```

---

# Video Metadata

Use `ffprobe` to read:

```
duration
creation_time
```

If `creation_time` is unavailable:

```
use file modification time
```

---

# Matching Sessions to Videos

A session belongs to a video if:

```
video.start_time <= session.start_time <= video.end_time
```

Compute clip start:

```
clip_start = session_start - video_start
```

---

# Timestamp Units

Timestamps may be:

```
seconds
milliseconds
```

Detect automatically:

```
if timestamp > 1e12:
    timestamp /= 1000
```

---

# Clip Planning

Add configurable padding.

```
start_sec -= pre_roll
end_sec += post_roll
```

Clamp to:

```
0 ≤ clip ≤ video duration
```

---

# FFmpeg Execution

Two modes supported.

### Reencode

```
ffmpeg
{extra_input_args}
-ss START
-to END
-i INPUT
-c:v libx264
-crf CRF
-preset PRESET
-c:a aac
{extra_output_args}
OUTPUT
```

### Copy

```
ffmpeg
{extra_input_args}
-ss START
-to END
-i INPUT
-c copy
{extra_output_args}
OUTPUT
```

Commands must be executed with:

```
subprocess.run(list[str])
```

Never use shell=True.

---

# Orchestrator Pipeline

Main pipeline:

```
load_config
read_sessions_from_db
scan_videos
probe_videos
match_sessions_to_videos
build_clip_plans
execute_ffmpeg
```

---

# CLI Interface

Program entrypoint:

```
bs-autocut config.toml
```

Implementation in `cli.py`.

---

# Logging

Use standard `logging`.

Log levels:

```
DEBUG
INFO
WARNING
ERROR
```

---

# Dry Run Mode

If enabled:

```
ffmpeg must NOT run
```

Instead print planned clips.

---

# Unit Tests

Tests must cover:

### filename_builder

* template replacement
* sanitization
* unique id

### clip_planner

* padding
* clamp logic

### matcher

* session/video overlap

Use pytest.

---

# Design Goals

The implementation must prioritize:

```
readability
modularity
testability
low dependencies
```

Each module must have a single responsibility.

---

# End of Specification


