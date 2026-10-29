import pytest

import llm
from llm import LLMError, generate_json, parse_json


def test_parse_plain_array():
    assert parse_json('[{"a": 1}]', list) == [{"a": 1}]


def test_parse_strips_fence_and_chatter():
    assert parse_json('Sure!\n```json\n[{"a": 1}]\n```\nHope that helps', list) == [{"a": 1}]


def test_parse_keeps_backticks_inside_a_json_string():
    # old code split on the first ``` and truncated fixed_code that contained markdown
    raw = '{"fixed_code": "```py\\nprint(1)\\n```", "summary": "s"}'
    assert parse_json(raw, dict)["fixed_code"].startswith("```py")


def test_parse_repairs_malformed_json():
    assert parse_json('[{"a": 1,}]', list) == [{"a": 1}]


def test_truncated_output_is_rejected_not_repaired():
    # a response cut off by the token limit must be retried, not "repaired" into a half-finished fixed_code
    with pytest.raises(LLMError):
        parse_json('{"summary": "s", "fixed_code": "def f():\\n    retu', dict)


def test_parse_rejects_wrong_type():
    with pytest.raises(LLMError):
        parse_json('{"a": 1}', list)


def test_parse_rejects_no_json():
    with pytest.raises(LLMError):
        parse_json("I could not review this code.", list)


def test_generate_json_retries_then_succeeds(fake_llm):
    answers = iter([RuntimeError("503 service unavailable"), "not json at all", '[{"ok": true}]'])

    def respond(system_prompt, user_message):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    fake_llm.respond = respond
    assert generate_json("sys", "user", list) == [{"ok": True}]
    assert fake_llm.calls == 3


def test_generate_json_raises_after_exhausting_retries(fake_llm):
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError("quota exceeded"))
    with pytest.raises(LLMError, match="quota exceeded"):
        generate_json("sys", "user", list)
    assert fake_llm.calls == llm.MAX_ATTEMPTS


def test_missing_credentials_are_not_retried(monkeypatch):
    def boom():
        raise llm.LLMUnrecoverableError("Gemini client could not be created")

    monkeypatch.setattr(llm, "_client", boom)
    with pytest.raises(LLMError, match="could not be created"):
        generate_json("sys", "user", list)


def test_unrecoverable_errors_skip_the_retry_loop(fake_llm):
    def respond(system_prompt, user_message):
        raise llm.LLMUnrecoverableError("cache miss in offline mode")

    fake_llm.respond = respond
    with pytest.raises(llm.LLMUnrecoverableError):
        generate_json("sys", "user", list)
    assert fake_llm.calls == 1


QUOTA_429 = ("429 RESOURCE_EXHAUSTED. {'error': {'message': 'Quota exceeded ... Please retry in 42.5s.', "
             "'details': [{'violations': [{'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'}]}]}}")


def test_rate_limit_waits_as_long_as_the_api_asks_and_keeps_the_attempts(fake_llm, monkeypatch):
    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    answers = iter([RuntimeError(QUOTA_429), RuntimeError(QUOTA_429), RuntimeError(QUOTA_429), '[{"ok": 1}]'])

    def respond(system_prompt, user_message):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    fake_llm.respond = respond
    # three 429s would have exhausted the three attempts under the old 2/4/8s backoff
    assert generate_json("sys", "user", list) == [{"ok": 1}]
    assert slept == [43.5, 43.5, 43.5]


def test_rate_limit_without_a_hint_uses_a_default_wait(fake_llm, monkeypatch):
    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    answers = iter([RuntimeError("429 RESOURCE_EXHAUSTED"), "[]"])

    def respond(system_prompt, user_message):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    fake_llm.respond = respond
    assert generate_json("sys", "user", list) == []
    assert slept == [llm.DEFAULT_RATE_LIMIT_DELAY + 1]


def test_a_huge_retry_hint_is_capped(fake_llm, monkeypatch):
    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    answers = iter([RuntimeError("429 ... Please retry in 3600s."), "[]"])

    def respond(system_prompt, user_message):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    fake_llm.respond = respond
    generate_json("sys", "user", list)
    assert slept == [llm.MAX_RATE_LIMIT_DELAY]


def test_daily_quota_is_not_waited_out(fake_llm, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: pytest.fail("must not sleep"))
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(
        RuntimeError("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    with pytest.raises(llm.LLMUnrecoverableError, match="daily"):
        generate_json("sys", "user", list)
    assert fake_llm.calls == 1


def test_endless_rate_limiting_eventually_gives_up(fake_llm, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    fake_llm.respond = lambda s, u: (_ for _ in ()).throw(RuntimeError(QUOTA_429))
    with pytest.raises(LLMError):
        generate_json("sys", "user", list)
    assert fake_llm.calls == llm.MAX_RATE_LIMIT_WAITS + llm.MAX_ATTEMPTS
