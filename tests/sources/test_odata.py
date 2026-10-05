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


class _Redirected(io.BytesIO):
    def geturl(self):
        return "https://www.knesset.gov.il/maintenance-page-geo"


def test_geo_redirect_is_a_block_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(odata.time, "sleep", lambda s: None)
    monkeypatch.setattr(odata.urllib.request, "urlopen", lambda req, timeout: calls.append(1) or _Redirected(b"<html>"))
    with pytest.raises(odata.SourceBlocked, match="maintenance-page-geo"):
        odata.ODataClient().rows("KNS_PlenumVote", {})
    assert len(calls) == 1


def test_proxy_only_for_knesset_hosts(monkeypatch):
    opened = []

    class Opener:
        def open(self, req, timeout):
            opened.append(req.full_url)
            return io.BytesIO(b'{"value": []}')

    monkeypatch.setenv("HKV_KNESSET_PROXY", "http://proxy.example:8888")
    monkeypatch.setattr(odata.urllib.request, "build_opener", lambda *handlers: Opener())
    monkeypatch.setattr(odata.urllib.request, "urlopen", lambda req, timeout: io.BytesIO(b'{"value": []}'))
    odata.ODataClient().rows("KNS_PlenumVote", {})
    odata.ODataClient(base_url="https://query.wikidata.org/sparql").rows("x", {})
    assert len(opened) == 1 and opened[0].startswith(odata.V4_URL)


def test_bad_request_is_not_retried(monkeypatch):
    codes = [400, 200]
    monkeypatch.setattr(odata.time, "sleep", lambda s: None)
    monkeypatch.setattr(odata.urllib.request, "urlopen", _fake_urlopen(codes))
    with pytest.raises(odata.SourceError, match="rejected"):
        odata.ODataClient().rows("KNS_PlenumVote", {})
    assert codes == [200]
