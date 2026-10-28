import asyncio
import json
import logging
import os
import sys
import time
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from models import ReviewRequest, ReviewResponse
from language_detector import detect_language
from tool_runner import run_tools
from output_normalizer import normalize
from agents.graph import review_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPECIALISTS = ("security", "performance", "maintainability")

app = FastAPI(title="Multi-Agent Code Review System")

# allow React dev server to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # quick check to verify server is running
    return {"status": "ok"}


def _analyze(request: ReviewRequest) -> tuple[str, dict, list[str]]:
    """Detect the language and run the static tools. Returns (language, initial graph state, warnings)."""
    language = request.language or detect_language(request.code, request.filename)
    report = run_tools(request.code, language, request.filename)
    normalized = normalize(report.outputs, request.filename)

    logger.info(
        "Language %s — findings: security %d, performance %d, maintainability %d",
        language,
        len(normalized["security_findings"]),
        len(normalized["performance_findings"]),
        len(normalized["maintainability_findings"]),
    )

    state = {
        "code":                     request.code,
        "language":                 language,
        "filename":                 request.filename,
        "tool_outputs":             report.outputs,
        "security_findings":        normalized["security_findings"],
        "performance_findings":     normalized["performance_findings"],
        "maintainability_findings": normalized["maintainability_findings"],
        "security_issues":          [],
        "performance_issues":       [],
        "maintainability_issues":   [],
        "failed_agents":            [],
        "warnings":                 [],
        "final_issues":             [],
        "summary":                  "",
        "fixed_code":               "",
    }
    return language, state, report.warnings


def _check_pipeline_health(failed_agents: list[str]) -> None:
    # if every specialist failed the "review" is an empty list that looks like a clean bill of health
    if set(SPECIALISTS) <= set(failed_agents):
        raise HTTPException(status_code=502, detail="All review agents failed — the LLM backend is unavailable or misconfigured")


@app.post("/review", response_model=ReviewResponse)
def review_code(request: ReviewRequest):
    start_time = time.time()
    session_id = uuid.uuid4()
    logger.info("Review started — session %s", session_id)

    language, state, tool_warnings = _analyze(request)

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
async def stream_review(request: ReviewRequest):
    async def event_generator():
        try:
            # run_tools blocks on subprocesses — keep it off the event loop
            language, state, tool_warnings = await asyncio.to_thread(_analyze, request)
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
