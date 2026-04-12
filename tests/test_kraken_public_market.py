import json

from app.adapters.kraken_public_market import _parse_ticker_payload


def test_parse_cli_payload_native_pair_key():
    """`kraken ticker -o json` shape: pair at top level, not REST `result` wrapper."""
    from app.adapters.kraken_public_market import _parse_cli_payload

    payload = {
        "XXBTZUSD": {
            "a": ["93000.0", "1", "1.000"],
            "b": ["92999.0", "2", "2.000"],
            "c": ["93000.0", "0.01000000"],
        }
    }
    last, bid, ask = _parse_cli_payload(payload)
    assert last == 93000.0
    assert bid == 92999.0
    assert ask == 93000.0


def test_parse_kraken_ticker_payload_minimal():
    raw = """
    {
      "error": [],
      "result": {
        "XBTUSD": {
          "a": ["93000.0", "1", "1.000"],
          "b": ["92999.0", "2", "2.000"],
          "c": ["93000.0", "0.01000000"]
        }
      }
    }
    """
    payload = json.loads(raw)
    last, bid, ask = _parse_ticker_payload(payload)
    assert last == 93000.0
    assert bid == 92999.0
    assert ask == 93000.0
