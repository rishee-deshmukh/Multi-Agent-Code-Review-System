from agents.base import SpecialistSpec, run_specialist
from agents.prompts import PERFORMANCE_PROMPT
from agents.state import AgentState

SPEC = SpecialistSpec(
    name="performance",
    prompt=PERFORMANCE_PROMPT,
    tools_label="Ruff PERF rules + ESLint performance rules",
)


def performance_agent(state: AgentState) -> dict:
    return run_specialist(SPEC, state)
