"""Unit tests for FearGreedCollector — all HTTP calls mocked via respx."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from src.etl.collectors.fear_greed import FearGreedCollector
from src.shared.exceptions import ExternalAPIError

# Fixed epoch timestamp used across tests: 2023-11-14T22:13:20Z
FIXED_TS = datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
FIXED_EPOCH_STR = str(int(FIXED_TS.timestamp()))  # "1700000000"

_FNG_URL = "https://api.alternative.me/fng/"

VALID_PAYLOAD: dict[str, object] = {
    "data": [
        {
            "value": "42",
            "value_classification": "Fear",
            "timestamp": FIXED_EPOCH_STR,
        }
    ]
}


class TestFearGreedCollectorFetchFearGreed:
    """Tests for FearGreedCollector.fetch_fear_greed."""

    @respx.mock
    async def test_returns_correct_value_and_classification(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 42
        assert result["value_classification"] == "Fear"

    @respx.mock
    async def test_returns_correct_utc_timestamp(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["timestamp"] == FIXED_TS
        assert result["timestamp"].tzinfo is UTC

    @respx.mock
    async def test_extreme_fear_classification(self) -> None:
        payload: dict[str, object] = {
            "data": [
                {
                    "value": "5",
                    "value_classification": "Extreme Fear",
                    "timestamp": FIXED_EPOCH_STR,
                }
            ]
        }
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=payload))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 5
        assert result["value_classification"] == "Extreme Fear"

    @respx.mock
    async def test_extreme_greed_classification(self) -> None:
        payload: dict[str, object] = {
            "data": [
                {
                    "value": "95",
                    "value_classification": "Extreme Greed",
                    "timestamp": FIXED_EPOCH_STR,
                }
            ]
        }
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=payload))

        async with FearGreedCollector() as collector:
            result = await collector.fetch_fear_greed()

        assert result["value"] == 95

    @respx.mock
    async def test_non_200_raises_external_api_error(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(503, text="Service Unavailable"))

        async with FearGreedCollector() as collector:
            with pytest.raises(ExternalAPIError):
                await collector.fetch_fear_greed()

    @respx.mock
    async def test_500_raises_external_api_error_with_status(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))

        async with FearGreedCollector() as collector:
            with pytest.raises(ExternalAPIError) as exc_info:
                await collector.fetch_fear_greed()

        assert "500" in str(exc_info.value)

    @respx.mock
    async def test_transport_error_raises_external_api_error(self) -> None:
        respx.get(_FNG_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        async with FearGreedCollector() as collector:
            with pytest.raises(ExternalAPIError, match="Network error"):
                await collector.fetch_fear_greed()


class TestFearGreedCollectorParseResponse:
    """Tests for the static _parse_response method (missing / malformed fields)."""

    def test_missing_data_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse_response({})

    def test_empty_data_list_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse_response({"data": []})

    def test_data_not_a_list_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unexpected"):
            FearGreedCollector._parse_response({"data": "not a list"})  # type: ignore[arg-type]

    def test_missing_value_field_raises_value_error(self) -> None:
        entry = {"value_classification": "Fear", "timestamp": FIXED_EPOCH_STR}
        with pytest.raises(ValueError, match="Missing required fields"):
            FearGreedCollector._parse_response({"data": [entry]})

    def test_missing_classification_raises_value_error(self) -> None:
        entry = {"value": "42", "timestamp": FIXED_EPOCH_STR}
        with pytest.raises(ValueError, match="Missing required fields"):
            FearGreedCollector._parse_response({"data": [entry]})

    def test_missing_timestamp_raises_value_error(self) -> None:
        entry = {"value": "42", "value_classification": "Fear"}
        with pytest.raises(ValueError, match="Missing required fields"):
            FearGreedCollector._parse_response({"data": [entry]})

    def test_non_numeric_value_raises_value_error(self) -> None:
        entry = {"value": "not_a_number", "value_classification": "Fear", "timestamp": FIXED_EPOCH_STR}
        with pytest.raises(ValueError, match="Cannot parse Fear & Greed value"):
            FearGreedCollector._parse_response({"data": [entry]})

    def test_non_numeric_timestamp_raises_value_error(self) -> None:
        entry = {"value": "42", "value_classification": "Fear", "timestamp": "bad-ts"}
        with pytest.raises(ValueError, match="Cannot parse Fear & Greed timestamp"):
            FearGreedCollector._parse_response({"data": [entry]})

    def test_valid_payload_returns_typed_dict(self) -> None:
        entry: dict[str, object] = {
            "value": "75",
            "value_classification": "Greed",
            "timestamp": FIXED_EPOCH_STR,
        }
        result = FearGreedCollector._parse_response({"data": [entry]})

        assert isinstance(result, dict)
        assert result["value"] == 75
        assert result["value_classification"] == "Greed"
        assert result["timestamp"].tzinfo is UTC


class TestFearGreedCollectorFetchAsOhlcv:
    """Tests for FearGreedCollector.fetch_as_ohlcv."""

    @respx.mock
    async def test_returns_ohlcv_record_list_with_one_element(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert len(records) == 1

    @respx.mock
    async def test_symbol_is_fear_greed(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert records[0].symbol == "FEAR_GREED"

    @respx.mock
    async def test_all_price_fields_equal_index_value(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        r = records[0]
        expected = Decimal("42")
        assert r.price_open == expected
        assert r.price_high == expected
        assert r.price_low == expected
        assert r.price_close == expected

    @respx.mock
    async def test_volume_is_zero(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert records[0].volume_24h == Decimal("0")

    @respx.mock
    async def test_source_is_alternative_me(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert records[0].source == "alternative.me"

    @respx.mock
    async def test_timeframe_is_1d(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert records[0].timeframe == "1D"

    @respx.mock
    async def test_timestamp_matches_api_value(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()

        assert records[0].timestamp == FIXED_TS


class TestFearGreedCollectorContextManager:
    """Tests for async context manager lifecycle."""

    @respx.mock
    async def test_context_manager_closes_client(self) -> None:
        respx.get(_FNG_URL).mock(return_value=httpx.Response(200, json=VALID_PAYLOAD))

        collector = FearGreedCollector()
        async with collector:
            await collector.fetch_fear_greed()

        assert collector._client.is_closed

    async def test_close_twice_does_not_raise(self) -> None:
        collector = FearGreedCollector()
        await collector.close()
        await collector.close()
