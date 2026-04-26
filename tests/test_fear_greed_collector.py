"""Tests for src/collectors/fear_greed_collector.py (sync, no respx needed)."""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.collectors.fear_greed_collector import FearGreedCollector, FearGreedResult

_FIXED_TS = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
_FIXED_EPOCH = str(int(_FIXED_TS.timestamp()))  # "1700000000"

_VALID_PAYLOAD = {
    "data": [
        {
            "value": "42",
            "value_classification": "Fear",
            "timestamp": _FIXED_EPOCH,
        }
    ]
}


# ---------------------------------------------------------------------------
# _parse (static, no HTTP)
# ---------------------------------------------------------------------------

class TestParse:
    def test_valid_payload_returns_typed_dict(self):
        result = FearGreedCollector._parse(_VALID_PAYLOAD)
        assert result["value"] == 42
        assert result["classification"] == "Fear"
        assert result["timestamp"] == _FIXED_TS

    def test_timestamp_is_utc_aware(self):
        result = FearGreedCollector._parse(_VALID_PAYLOAD)
        assert result["timestamp"].tzinfo is timezone.utc

    def test_extreme_fear_value(self):
        payload = {"data": [{"value": "5", "value_classification": "Extreme Fear", "timestamp": _FIXED_EPOCH}]}
        result = FearGreedCollector._parse(payload)
        assert result["value"] == 5
        assert result["classification"] == "Extreme Fear"

    def test_extreme_greed_value(self):
        payload = {"data": [{"value": "95", "value_classification": "Extreme Greed", "timestamp": _FIXED_EPOCH}]}
        result = FearGreedCollector._parse(payload)
        assert result["value"] == 95

    def test_missing_data_key_raises_value_error(self):
        import pytest
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse({})

    def test_empty_data_list_raises_value_error(self):
        import pytest
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse({"data": []})

    def test_data_not_list_raises_value_error(self):
        import pytest
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse({"data": "bad"})

    def test_missing_value_field_raises_value_error(self):
        import pytest
        entry = {"value_classification": "Fear", "timestamp": _FIXED_EPOCH}
        with pytest.raises(ValueError, match="Missing fields"):
            FearGreedCollector._parse({"data": [entry]})

    def test_missing_classification_raises_value_error(self):
        import pytest
        entry = {"value": "42", "timestamp": _FIXED_EPOCH}
        with pytest.raises(ValueError, match="Missing fields"):
            FearGreedCollector._parse({"data": [entry]})

    def test_missing_timestamp_raises_value_error(self):
        import pytest
        entry = {"value": "42", "value_classification": "Fear"}
        with pytest.raises(ValueError, match="Missing fields"):
            FearGreedCollector._parse({"data": [entry]})

    def test_non_numeric_value_raises_value_error(self):
        import pytest
        entry = {"value": "not_a_number", "value_classification": "Fear", "timestamp": _FIXED_EPOCH}
        with pytest.raises(ValueError, match="Cannot parse value"):
            FearGreedCollector._parse({"data": [entry]})

    def test_non_numeric_timestamp_raises_value_error(self):
        import pytest
        entry = {"value": "42", "value_classification": "Fear", "timestamp": "bad-ts"}
        with pytest.raises(ValueError, match="Cannot parse timestamp"):
            FearGreedCollector._parse({"data": [entry]})


# ---------------------------------------------------------------------------
# fetch (mocked HTTP)
# ---------------------------------------------------------------------------

def _mock_response(status: int, json_body: dict):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    if status >= 400:
        import httpx
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=r
        )
    return r


class TestFetch:
    def _patch_get(self, response):
        return patch(
            "src.collectors.fear_greed_collector.httpx.Client",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(get=MagicMock(return_value=response))),
                __exit__=MagicMock(return_value=False),
            ),
        )

    def test_returns_fear_greed_result(self):
        resp = _mock_response(200, _VALID_PAYLOAD)
        with self._patch_get(resp):
            with FearGreedCollector() as collector:
                # Override internal client directly
                collector._client = MagicMock()
                collector._client.get.return_value = resp
                result = collector.fetch()
        assert result["value"] == 42
        assert result["classification"] == "Fear"

    def test_http_error_propagates(self):
        import pytest, httpx
        resp = _mock_response(503, {})
        collector = FearGreedCollector()
        collector._client = MagicMock()
        collector._client.get.return_value = resp
        with pytest.raises(httpx.HTTPStatusError):
            collector.fetch()

    def test_malformed_response_raises_value_error(self):
        import pytest
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"data": []}
        collector = FearGreedCollector()
        collector._client = MagicMock()
        collector._client.get.return_value = resp
        with pytest.raises(ValueError):
            collector.fetch()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_close_is_called_on_exit(self):
        collector = FearGreedCollector()
        collector._client = MagicMock()
        with collector:
            pass
        collector._client.close.assert_called_once()

    def test_returns_self_on_enter(self):
        collector = FearGreedCollector()
        collector._client = MagicMock()
        with collector as c:
            assert c is collector
