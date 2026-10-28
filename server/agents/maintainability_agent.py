from agents.base import SpecialistSpec, run_specialist
from agents.prompts import MAINTAINABILITY_PROMPT
from agents.state import AgentState

SPEC = SpecialistSpec(
    name="maintainability",
    prompt=MAINTAINABILITY_PROMPT,
    tools_label="Ruff + ESLint style rules",
)


def maintainability_agent(state: AgentState) -> dict:
    return run_specialist(SPEC, state)
