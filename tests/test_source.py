import io
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from krakow_air import source


def test_retry_then_success(monkeypatch, day):
    open_url = Mock(side_effect=[URLError("timeout"), io.BytesIO(b'{"ok":true}')])
    sleep = Mock()
    monkeypatch.setattr(source, "urlopen", open_url)
    monkeypatch.setattr(source.time, "sleep", sleep)
    assert source.fetch(day) == {"ok": True}
    sleep.assert_called_once_with(1)
    query = parse_qs(urlsplit(open_url.call_args.args[0]).query)
    assert query["start_date"] == query["end_date"] == [day.isoformat()]
    assert query["hourly"] == ["pm2_5,pm10,european_aqi"]
    assert query["domains"] == ["cams_europe"]


@pytest.mark.parametrize(("status", "attempts"), [(400, 1), (429, 3), (503, 3)])
def test_http_failure(monkeypatch, day, status, attempts):
    request = Mock(side_effect=HTTPError(source.ENDPOINT, status, "test", {}, None))
    monkeypatch.setattr(source, "urlopen", request)
    monkeypatch.setattr(source.time, "sleep", Mock())
    with pytest.raises(HTTPError):
        source.fetch(day)
    assert request.call_count == attempts
