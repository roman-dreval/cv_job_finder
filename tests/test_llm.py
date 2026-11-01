import json
import subprocess
from dataclasses import replace

import pytest

from job_finder import config, grounding, hardware, llm
from job_finder.settings import Settings
from job_finder.sources import Job


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_evaluate_sends_only_the_truncated_ad(monkeypatch):
    sent = {}
    answer = {"requirements": [{"requirement": "Python", "required": True, "match": "yes"}], "blockers": [],
              "summary": "Good fit"}

    def fake_post(url, **kwargs):
        sent.update(url=url, **kwargs)
        return FakeResponse({"model": config.MODEL_ID, "choices": [{"message": {"content": json.dumps(answer)}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    job = Job(url="u", source="Jobicy", title="Python Dev", company="ACME", city="Prague",
              published="2026-10-01", description="x" * 20000)

    result = llm.evaluate(job, "RULES-TEXT")

    assert result == answer  # the program counts the score
    assert sent["url"] == f"{config.LM_URL}/chat/completions"
    body = sent["json"]
    assert body["model"] == config.MODEL_ID
    assert body["response_format"]["type"] == "json_schema"
    assert body["messages"][0]["content"] == "RULES-TEXT"  # no CV: the model can't list the candidate's skills
    assert body["reasoning_effort"] == "none"  # no thinking: it ate the whole answer of Gemma 4 and took 30 s
    user = body["messages"][1]["content"]
    assert "Python Dev" in user and "ACME" in user and "Prague" in user
    assert user.count("x") == config.MAX_DESCRIPTION_CHARS
    assert user.startswith("Title: Python Dev\nCompany: ACME\nLocation: Prague\nSource: Jobicy\n\n")


def test_evaluate_rejects_answer_from_another_model(monkeypatch):
    # If our model was unloaded (e.g. from the LM Studio window), the server answers with another model
    answer = {"requirements": [], "blockers": [], "summary": ""}
    monkeypatch.setattr(llm.requests, "post", lambda url, **kwargs: FakeResponse(
        {"model": "qwen/qwen3.8-27b", "choices": [{"message": {"content": json.dumps(answer)}}]}))
    job = Job(url="u", source="Jobicy", title="Python Dev", company="ACME", city="", published="2026-10-01",
              description="")
    with pytest.raises(llm.ModelLost, match="qwen/qwen3.8-27b"):
        llm.evaluate(job, "RULES")


def test_prepare_starts_server_without_capturing_output(tmp_path, monkeypatch):
    # The LM Studio service started by the command may inherit captured output pipes,
    # and then subprocess.run waits for them to close forever, despite the timeout
    exe = tmp_path / "lms.exe"
    exe.write_text("")
    monkeypatch.setattr(config, "LMS_EXE", exe)
    states = iter([False, True])
    monkeypatch.setattr(llm, "_server_up", lambda: next(states))
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args[1:], kwargs))
        return subprocess.CompletedProcess(args, 0, stdout=f'[{{"identifier": "{config.MODEL_ID}"}}]', stderr="")

    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    llm.prepare(config.MODEL)
    (start_args, start_kwargs), (ps_args, _) = calls
    assert start_args[:2] == ["server", "start"]
    assert start_kwargs.get("stdout") is subprocess.DEVNULL
    assert start_kwargs.get("stderr") is subprocess.DEVNULL
    assert ps_args == ["ps", "--json"]


def test_the_rules_are_the_same_for_everyone():
    s = Settings(cv_path="a", skills=["Kotlin"], main_skill="Kotlin", city="Brno", remote=False,
                 levels=["intern", "junior"], languages={"English": "C1", "Russian": "Native"})
    rules = llm.render_rules(s)
    # The profile is the program's part: the model only takes the facts out of the ad
    assert rules == llm.render_rules(replace(s, city="Praha", levels=["senior"], languages={"English": "B2"},
                                             education="master", areas=["Frontend"]))
    assert "Brno" not in rules and "Kotlin" not in rules and "Russian" not in rules
    assert rules.endswith("Write all texts in English, as plain text without Markdown." + chr(10))


def test_fingerprint_ignores_the_profile():
    s = Settings(cv_path="a", skills=["Python"], main_skill="Python", languages={"English": "B2"})
    assert llm.fingerprint(s) == llm.fingerprint(replace(s, skills=["Go"], main_skill="Go", min_score=7,
                                                         levels=["mid"], languages={"English": "C1"}))


def test_fingerprint_uses_model(monkeypatch):
    s = Settings(cv_path="a", skills=["Python"], main_skill="Python", languages={"English": "B2"})
    assert llm.model_name(s) == config.MODEL  # chosen by the graphics card (12 GB in the tests' fixture)
    assert llm.fingerprint(s) == f"{config.MODEL}\n{llm.render_rules(s)}"  # the author's key stays the same
    small = replace(s, model="google/gemma-4-e4b")
    assert llm.model_name(small) == "google/gemma-4-e4b" and llm.fingerprint(small) != llm.fingerprint(s)
    monkeypatch.setattr(hardware, "default_model", lambda: "google/gemma-4-e4b")  # a 6 GB card
    assert llm.model_name(s) == "google/gemma-4-e4b"


def test_prepare_reloads_another_model(tmp_path, monkeypatch):
    exe = tmp_path / "lms.exe"
    exe.write_text("")
    monkeypatch.setattr(config, "LMS_EXE", exe)
    monkeypatch.setattr(llm, "_server_up", lambda: True)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args[1:])
        out = (f'[{{"identifier": "{config.MODEL_ID}", "modelKey": "google/gemma-4-12b"}}]'
               if args[1] == "ps" else "")
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")

    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    llm.prepare("google/gemma-4-e4b")  # another model is loaded under our name
    assert [call[0] for call in calls] == ["ps", "unload", "load"] and calls[2][1] == "google/gemma-4-e4b"
    calls.clear()
    llm.prepare("google/gemma-4-12b")  # the right one is loaded already
    assert [call[0] for call in calls] == ["ps"]


def test_downloaded_models_reads_lms_output_from_a_file(monkeypatch):
    # Not a pipe: lms may start LM Studio's service, which would inherit a pipe and keep the call waiting forever
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs)
        kwargs["stdout"].write('[{"type": "llm", "modelKey": "google/gemma-4-12b"}]')
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    assert llm.downloaded_models() == {"google/gemma-4-12b"}
    assert hasattr(seen["stdout"], "fileno") and seen["stdout"] is not subprocess.PIPE and "capture_output" not in seen


def test_clean_output():
    assert llm.clean_output("\x1b[31mError\x1b[0m: no model\n") == "Error: no model"
    assert llm.clean_output("x" * 500) == "x" * 300


def test_evaluate_ends_the_ad_with_the_programs_facts(monkeypatch):
    sent = {}
    answer = {"requirements": [], "blockers": [], "summary": ""}

    def fake_post(url, **kwargs):
        sent.update(kwargs)
        return FakeResponse({"model": config.MODEL_ID, "choices": [{"message": {"content": json.dumps(answer)}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    job = Job(url="u", source="Jobicy", title="Dev", company="A", city="", published="", description="We use C#.")
    llm.evaluate(job, "RULES", "Technologies a program found written in this ad: C#/.NET.")
    assert sent["json"]["messages"][1]["content"].endswith(
        "We use C#.\n\nTechnologies a program found written in this ad: C#/.NET.")


def test_the_rules_ask_for_the_ads_facts_without_the_candidate():
    rules = llm.render_rules(Settings())
    assert "You don't see the candidate" in rules and "CV" not in rules
    assert "at most 8" in rules and 'write them together with "or"' in rules
    assert "not what the person will do or learn" in rules and "never from its duties" in rules
    assert "nor an interest it hopes for" in rules and "fields of study" in rules
    assert "Machine learning / AI" in rules and '"Not IT"' in rules  # the areas to choose from
    properties = llm.SCHEMA["properties"]
    areas = properties["areas"]["items"]["enum"]
    assert areas[:2] == ["Backend", "Frontend"] and "Not IT" in areas
    assert properties["degree"]["enum"] == list(grounding.DEGREES)
    assert properties["citizenship"] == {"type": "string"} and "citizenship — the citizenship" in rules
    assert "doesn't discriminate" in rules
    for key in ("must_have", "nice_to_have"):  # the ad's words; the program decides what the CV has
        assert properties[key] == {"type": "array", "items": {"type": "string"}, "maxItems": 8}
    assert set(llm.SCHEMA["required"]) == set(properties)
