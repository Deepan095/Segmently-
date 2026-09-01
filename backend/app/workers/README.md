# Workers

The media pipeline runs as four sequential job types - `download`, `transcribe`, `segment`, and `render` - each executed by an [arq](https://arq-docs.helpmanual.io/) worker process against the Redis queue (`REDIS_URL`), one `ProcessingJob` row per stage with its own status and progress. Request handlers only enqueue jobs and return `202`; they never download media, run Whisper, call Claude, or invoke FFmpeg inline. Every job must be idempotent and retryable so a re-run or a crash mid-stage leaves the project in a recoverable state.
