import asyncio
import json
import logging
import os
import sys
import time
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from dotenv import load_dotenv

load_dotenv()

from models import ReviewRequest, ReviewResponse
from pipeline import analyze
from agents.graph import review_graph
from limits import RequestGuard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPECIALISTS = ("security", "performance", "maintainability")

app = FastAPI(title="Multi-Agent Code Review System")

guard = RequestGuard.from_env()

# CORS_ORIGINS is a comma-separated list. The default is the Vite dev server; the production image
# serves the UI from the same origin as the API and needs no CORS at all.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # quick check to verify server is running
    return {"status": "ok"}


def _check_pipeline_health(failed_agents: list[str]) -> None:
    # if every specialist failed the "review" is an empty list that looks like a clean bill of health
    if set(SPECIALISTS) <= set(failed_agents):
        raise HTTPException(status_code=502, detail="All review agents failed — the LLM backend is unavailable or misconfigured")


@app.post("/review", response_model=ReviewResponse)
def review_code(request: ReviewRequest, http_request: Request):
    with guard.admitted(http_request, request.code):
        return _review(request)


def _review(request: ReviewRequest) -> ReviewResponse:
    start_time = time.time()
    session_id = uuid.uuid4()
    logger.info("Review started — session %s", session_id)

    language, state, tool_warnings = analyze(request.code, request.filename, request.language)

    try:
        result = review_graph.invoke(state)
    except Exception as e:
        logger.error("LangGraph pipeline failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

    _check_pipeline_health(result.get("failed_agents", []))

    final_issues = result.get("final_issues", [])
    processing_time = int((time.time() - start_time) * 1000)
    logger.info("Review complete — %d issues in %dms", len(final_issues), processing_time)

    return ReviewResponse(
        session_id=session_id,
        language=language,
        issues=final_issues,
        total_issues=len(final_issues),
        summary=result.get("summary", ""),
        fixed_code=result.get("fixed_code") or request.code,
        processing_time_ms=processing_time,
        warnings=tool_warnings + result.get("warnings", []),
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/stream")
async def stream_review(request: ReviewRequest, http_request: Request):
    ticket = guard.admit(http_request, request.code)

    async def event_generator():
        try:
            # run_tools blocks on subprocesses — keep it off the event loop
            language, state, tool_warnings = await asyncio.to_thread(analyze, request.code, request.filename, request.language)
            yield _sse({"event": "language", "language": language})
            yield _sse({"event": "tools_done", "warnings": tool_warnings})

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def run_graph():
                try:
                    for chunk in review_graph.stream(state):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

            loop.run_in_executor(None, run_graph)

            failed_agents: list[str] = []
            agent_warnings: list[str] = []

            while (chunk := await queue.get()) is not None:
                if isinstance(chunk, Exception):
                    raise chunk

                # parallel nodes can land in one chunk — handle every key, not just the first
                for node, update in chunk.items():
                    failed_agents += update.get("failed_agents", [])
                    agent_warnings += update.get("warnings", [])

                    if node in SPECIALISTS:
                        issues = update.get(f"{node}_issues", [])
                        yield _sse({"event": f"{node}_done", "issues": [i.model_dump() for i in issues]})

                    elif node == "synthesizer":
                        _check_pipeline_health(failed_agents)
                        yield _sse({
                            "event": "synthesis_done",
                            "issues": [i.model_dump() for i in update.get("final_issues", [])],
                            "summary": update.get("summary", ""),
                            "fixed_code": update.get("fixed_code") or request.code,
                            "warnings": tool_warnings + agent_warnings,
                        })

            yield _sse({"event": "done"})

        except HTTPException as e:
            yield _sse({"event": "error", "detail": e.detail})
        except Exception as e:
            logger.exception("Stream failed")
            yield _sse({"event": "error", "detail": f"Pipeline failed: {e}"})
        finally:
            ticket.release()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        # the generator never runs if the client disconnects first, so release the slot here as well
        background=BackgroundTask(ticket.release),
    )


# The production image bundles the built React app and serves it from the same origin as the API.
# Mounted last so /health, /review and /stream take precedence.
_default_static = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client", "dist")
STATIC_DIR = os.getenv("STATIC_DIR", _default_static)
if os.path.isfile(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
