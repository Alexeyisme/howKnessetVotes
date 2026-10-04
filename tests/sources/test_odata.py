import io
import urllib.error

import pytest

from hkv.sources import odata


def _fake_urlopen(codes):
    """urlopen stand-in answering with the HTTP codes in order (200 -> an empty v4 page)."""
    def urlopen(req, timeout):
        code = codes.pop(0)
        if code != 200:
            raise urllib.error.HTTPError(req.full_url, code, "", {}, io.BytesIO())
        return io.BytesIO(b'{"value": []}')
    return urlopen


def test_throttle_481_is_retried(monkeypatch):
    monkeypatch.setattr(odata.time, "sleep", lambda s: None)
    monkeypatch.setattr(odata.urllib.request, "urlopen", _fake_urlopen([481, 481, 200]))
    assert odata.ODataClient().rows("KNS_PlenumVote", {}) == []


def test_bad_request_is_not_retried(monkeypatch):
    codes = [400, 200]
    monkeypatch.setattr(odata.time, "sleep", lambda s: None)
    monkeypatch.setattr(odata.urllib.request, "urlopen", _fake_urlopen(codes))
    with pytest.raises(odata.SourceError, match="rejected"):
        odata.ODataClient().rows("KNS_PlenumVote", {})
    assert codes == [200]
