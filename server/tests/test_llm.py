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
    answers = iter([RuntimeError("429"), "not json at all", '[{"ok": true}]'])

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
