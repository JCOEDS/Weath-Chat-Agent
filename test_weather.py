from unittest.mock import Mock
from uuid import uuid4

import pytest
import requests
from openai import APIConnectionError

import Weather_Chat_Agent
from Weather_Chat_Agent import SimpleTraceHandler, get_weather


def test_supported_city_returns_weather(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "current_weather": {
            "weathercode": 0,
            "temperature": 18,
            "windspeed": 12,
        }
    }
    mock_get = Mock(return_value=response)
    monkeypatch.setattr("Weather_Chat_Agent.requests.get", mock_get)

    result = get_weather.invoke({"city": "北京"})

    assert "北京" in result
    assert "晴" in result
    assert "18°C" in result
    assert "12 km/h" in result


@pytest.mark.parametrize(
    ("city", "latitude", "longitude"),
    [
        ("北京", 39.9042, 116.4074),
        ("上海", 31.2304, 121.4737),
        ("广州", 23.1291, 113.2644),
    ],
)
def test_supported_city_uses_correct_coordinates(
    monkeypatch, city, latitude, longitude
):
    response = Mock()
    response.json.return_value = {
        "current_weather": {
            "weathercode": 0,
            "temperature": 18,
            "windspeed": 12,
        }
    }
    mock_get = Mock(return_value=response)
    monkeypatch.setattr("Weather_Chat_Agent.requests.get", mock_get)

    get_weather.invoke({"city": city})

    assert mock_get.call_args.kwargs["params"] == {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True,
    }
    assert mock_get.call_args.kwargs["timeout"] == 5


def test_unsupported_city_does_not_call_weather_api(monkeypatch):
    mock_get = Mock()
    monkeypatch.setattr("Weather_Chat_Agent.requests.get", mock_get)

    result = get_weather.invoke({"city": "深圳"})

    assert "暂未收录深圳" in result
    mock_get.assert_not_called()


def test_unknown_weather_code_uses_fallback(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "current_weather": {
            "weathercode": 999,
            "temperature": 20,
            "windspeed": 5,
        }
    }
    monkeypatch.setattr(
        "Weather_Chat_Agent.requests.get",
        Mock(return_value=response),
    )

    result = get_weather.invoke({"city": "上海"})

    assert "未知天气(999)" in result


def test_http_error_is_reported(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503 Server Error")
    monkeypatch.setattr(
        "Weather_Chat_Agent.requests.get",
        Mock(return_value=response),
    )

    result = get_weather.invoke({"city": "广州"})

    assert "HTTPError" in result
    assert "503 Server Error" in result


def test_request_timeout_is_reported(monkeypatch):
    mock_get = Mock(side_effect=requests.Timeout("request timed out"))
    monkeypatch.setattr("Weather_Chat_Agent.requests.get", mock_get)

    result = get_weather.invoke({"city": "北京"})

    assert "Timeout" in result
    assert "request timed out" in result


@pytest.mark.parametrize(
    ("response_data", "missing_field"),
    [
        ({}, "current_weather"),
        ({"current_weather": {"weathercode": 0, "windspeed": 12}}, "temperature"),
        ({"current_weather": {"weathercode": 0, "temperature": 18}}, "windspeed"),
    ],
)
def test_incomplete_api_response_is_reported(
    monkeypatch, response_data, missing_field
):
    response = Mock()
    response.json.return_value = response_data
    monkeypatch.setattr(
        "Weather_Chat_Agent.requests.get",
        Mock(return_value=response),
    )

    result = get_weather.invoke({"city": "北京"})

    assert "KeyError" in result
    assert missing_field in result


def test_model_connection_error_is_reported_without_crashing(
    monkeypatch, capsys
):
    agent = Mock()
    agent.invoke.side_effect = APIConnectionError(
        message="network unavailable",
        request=Mock(),
    )
    monkeypatch.setattr(Weather_Chat_Agent, "ChatDeepSeek", Mock())
    monkeypatch.setattr(
        Weather_Chat_Agent,
        "create_agent",
        Mock(return_value=agent),
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "builtins.input",
        Mock(side_effect=["北京天气怎么样？", "quit"]),
    )

    Weather_Chat_Agent.main()

    output = capsys.readouterr().out
    assert "APIConnectionError" in output
    assert "network unavailable" in output
    agent.invoke.assert_called_once()
    callbacks = agent.invoke.call_args.kwargs["config"]["callbacks"]
    assert len(callbacks) == 1
    assert isinstance(callbacks[0], SimpleTraceHandler)


def test_trace_handler_logs_events_without_prompt_or_tool_content(capsys):
    handler = SimpleTraceHandler()
    model_run_id = uuid4()
    tool_run_id = uuid4()
    private_text = "private prompt and API key"

    handler.on_chat_model_start(
        {"name": "DeepSeek"},
        [[private_text]],
        run_id=model_run_id,
    )
    handler.on_llm_end(Mock(), run_id=model_run_id)
    handler.on_tool_start(
        {"name": "get_weather"},
        private_text,
        run_id=tool_run_id,
    )
    handler.on_tool_end(private_text, run_id=tool_run_id)

    output = capsys.readouterr().out
    assert "[追踪] 模型开始：聊天模型" in output
    assert "[追踪] 模型完成（耗时 " in output
    assert "[追踪] 工具开始：天气查询工具" in output
    assert "[追踪] 工具完成（耗时 " in output
    assert private_text not in output
