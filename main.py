from __future__ import annotations

import csv
import io
import json
import logging
import os
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

logger = logging.getLogger("demo")
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_CLOUD_MODEL = os.getenv("YANDEX_CLOUD_MODEL", "qwen3-235b-a22b-fp8/latest")

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"

app = FastAPI(title="Code Interpreter Demo")

client = openai.OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
)


def _parse_csv_preview(content: bytes, filename: str) -> dict[str, Any]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"filename": filename, "columns": [], "preview_rows": [], "row_count": 0}

    columns = rows[0]
    data_rows = rows[1:]
    preview = data_rows[:10]
    return {
        "filename": filename,
        "columns": columns,
        "preview_rows": preview,
        "row_count": len(data_rows),
    }


# ── API Endpoints ──────────────────────────────────────────────


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        content = await f.read()
        preview = _parse_csv_preview(content, f.filename or "file.csv")

        yc_file = client.files.create(
            file=(f.filename, content, "text/csv"),
            purpose="assistants",
        )

        results.append({
            "file_id": yc_file.id,
            "filename": f.filename,
            "columns": preview["columns"],
            "preview_rows": preview["preview_rows"],
            "row_count": preview["row_count"],
        })
    return JSONResponse(results)


@app.get("/api/analyze")
async def analyze(
    query: str = Query(...),
    file_ids: list[str] = Query(default=[]),
):
    container_cfg: dict[str, Any] = {"type": "auto"}
    if file_ids:
        container_cfg["file_ids"] = file_ids

    async def event_stream():
        resp_id: str | None = None
        try:
            stream = client.responses.create(
                model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_CLOUD_MODEL}",
                input=query,
                tool_choice="auto",
                temperature=0.3,
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": container_cfg,
                    }
                ],
                stream=True,
            )

            code_block_idx = 0

            for event in stream:
                etype = event.type

                if etype.startswith("response.code_interpreter") or etype == "response.output_item.done":
                    logger.info("EVENT %s | attrs: %s", etype, dir(event))
                    if hasattr(event, "__dict__"):
                        logger.info("EVENT %s | dict: %s", etype, {
                            k: (repr(v)[:200] if isinstance(v, str) else type(v).__name__)
                            for k, v in vars(event).items()
                            if not k.startswith("_")
                        })

                if etype == "response.output_text.delta":
                    yield _sse("text_delta", {"delta": event.delta})

                elif etype == "response.code_interpreter_call_code.delta":
                    yield _sse("code_delta", {"delta": event.delta})

                elif etype == "response.code_interpreter_call_code.done":
                    code_block_idx += 1
                    code_text = getattr(event, "code", "") or getattr(event, "data", "") or ""
                    logger.info("code_done -> code_text length: %d", len(code_text))
                    yield _sse("code_generated", {
                        "code": code_text,
                        "block": code_block_idx,
                    })

                elif etype == "response.code_interpreter_call.in_progress":
                    yield _sse("code_running", {"block": code_block_idx})

                elif etype == "response.code_interpreter_call.interpreting":
                    yield _sse("code_interpreting", {"block": code_block_idx})

                elif etype == "response.code_interpreter_call.completed":
                    yield _sse("code_completed", {"block": code_block_idx})

                elif etype == "response.output_item.done":
                    item = getattr(event, "item", None)
                    if item and getattr(item, "type", "") == "code_interpreter_call":
                        code_text = getattr(item, "code", "") or ""
                        outputs = []
                        for out in getattr(item, "outputs", []):
                            logs = getattr(out, "logs", "")
                            if logs:
                                outputs.append(logs)
                        yield _sse("code_result", {
                            "code": code_text,
                            "outputs": outputs,
                            "block": code_block_idx,
                        })

                elif etype == "response.reasoning_text.delta":
                    yield _sse("reasoning_delta", {"delta": event.delta})

                elif etype == "response.reasoning_summary_text.delta":
                    yield _sse("reasoning_delta", {"delta": event.delta})

                elif etype == "response.in_progress":
                    resp_id = event.response.id
                    yield _sse("processing", {"response_id": resp_id})

            # After stream ends, retrieve full response for file annotations
            if resp_id:
                full_response = client.responses.retrieve(resp_id)
                files_info = _extract_files(full_response)
                if files_info:
                    yield _sse("files", {"files": files_info})

            yield _sse("done", {})

        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _extract_files(response: Any) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if hasattr(content, "annotations") and content.annotations:
                    for ann in content.annotations:
                        if ann.type == "container_file_citation":
                            files.append({
                                "file_id": ann.file_id,
                                "filename": ann.filename,
                            })
    return files


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    try:
        client.files.delete(file_id)
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str, filename: str = Query(default="file")):
    content = client.files.content(file_id)
    data = content.read()

    ext = Path(filename).suffix.lower()
    content_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".json": "application/json",
    }
    ct = content_type_map.get(ext, "application/octet-stream")

    return Response(
        content=data,
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/sample-data")
async def list_sample_data():
    samples = []
    for p in sorted(SAMPLE_DATA_DIR.glob("*.csv")):
        content = p.read_bytes()
        preview = _parse_csv_preview(content, p.name)
        samples.append(preview)
    return JSONResponse(samples)


@app.post("/api/upload-sample")
async def upload_sample(filenames: list[str]):
    results = []
    for name in filenames:
        path = SAMPLE_DATA_DIR / name
        if not path.exists():
            continue
        content = path.read_bytes()
        preview = _parse_csv_preview(content, name)
        yc_file = client.files.create(
            file=(name, content, "text/csv"),
            purpose="assistants",
        )
        results.append({
            "file_id": yc_file.id,
            "filename": name,
            "columns": preview["columns"],
            "preview_rows": preview["preview_rows"],
            "row_count": preview["row_count"],
        })
    return JSONResponse(results)


# ── Static files & SPA ────────────────────────────────────────

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
