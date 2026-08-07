import pytest
from unittest.mock import patch, MagicMock
import httpx
from google.genai import errors

from survey.services.gemini import generate_summary
from survey.services.summary import build_answers_text, build_prompt, summarize_answers
from survey.services.exceptions import AIServiceUnavailable

#! ================================================================
#!                    gemini.generate_summary
#! ================================================================

def test_generate_summary_returns_response_text_on_success():
    fake_response = MagicMock()
    fake_response.text = "a short summary"

    # patch() targets survey.services.gemini.client - that's where the
    # instantiated client lives and gets *used*
    with patch('survey.services.gemini.client.models.generate_content', return_value=fake_response) as mock_generate:
        result = generate_summary("some prompt", model="gemini-3.1-flash-lite")

    assert result == "a short summary"
    mock_generate.assert_called_once_with(model="gemini-3.1-flash-lite", contents="some prompt")

def test_generate_summary_raises_ai_service_unavailable_on_api_error():
    # errors.APIError(code, response_json, response=None) - response_json
    # mirrors the JSON body Google's API sends back on a real failure.
    api_error = errors.APIError(500, {"error": {"code": 500, "message": "boom", "status": "INTERNAL"}})

    with patch('survey.services.gemini.client.models.generate_content', side_effect=api_error):
        with pytest.raises(AIServiceUnavailable):
            generate_summary("some prompt")


def test_generate_summary_raises_ai_service_unavailable_on_httpx_error():
    http_error = httpx.HTTPError("connection failed")

    with patch('survey.services.gemini.client.models.generate_content', side_effect=http_error):
        with pytest.raises(AIServiceUnavailable):
            generate_summary("some prompt")

def test_generate_summary_does_not_catch_unrelated_exceptions():
    # sanity check on the except clause: only APIError/HTTPError are caught.
    # anything else (a bug in your own code, say) should propagate normally,
    # not get silently swallowed into a generic "AI service unavailable".
    with patch('survey.services.gemini.client.models.generate_content', side_effect=ValueError("weird bug")):
        with pytest.raises(ValueError):
            generate_summary("some prompt")

#! ================================================================
#!              summary.build_answers_text / build_prompt
#! ================================================================

def test_build_answers_text_numbers_each_answer():
    result = build_answers_text(["good", "bad", "ok"])
    assert result == "1. good\n2. bad\n3. ok"


def test_build_answers_text_empty_list_returns_empty_string():
    assert build_answers_text([]) == ""


def test_build_prompt_includes_question_and_answers():
    prompt = build_prompt("How was it?", "1. good")
    assert "How was it?" in prompt
    assert "1. good" in prompt

#! ================================================================
#!                   summary.summarize_answers
#! ================================================================

def test_summarize_answers_calls_generate_summary_with_built_prompt():
    # patch() targets survey.services.summary.generate_summary - the name
    # as imported and used inside summary.py, not where it's defined.
    with patch('survey.services.summary.generate_summary', return_value="final summary") as mock_generate:
        result = summarize_answers("How was it?", ["good", "bad"])

    assert result == "final summary"
    mock_generate.assert_called_once()
    called_prompt = mock_generate.call_args[0][0]
    assert "How was it?" in called_prompt
    assert "1. good" in called_prompt
    assert "2. bad" in called_prompt


def test_summarize_answers_propagates_ai_service_unavailable():
    with patch('survey.services.summary.generate_summary', side_effect=AIServiceUnavailable("down")):
        with pytest.raises(AIServiceUnavailable):
            summarize_answers("How was it?", ["good"])