from agents.base import SpecialistSpec, run_specialist
from agents.prompts import SECURITY_PROMPT
from agents.state import AgentState

SPEC = SpecialistSpec(
    name="security",
    prompt=SECURITY_PROMPT,
    tools_label="Semgrep + Bandit",
)


def security_agent(state: AgentState) -> dict:
    return run_specialist(SPEC, state)
