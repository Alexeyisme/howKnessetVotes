#!/usr/bin/env python3
"""HTTPS proxy that only reaches knesset.gov.il, for the Knesset geo-block (docs/knesset-proxy.md).

The Knesset refuses requests from outside Israel. This runs on a server in Israel and listens on 127.0.0.1 only;
an SSH tunnel from the main server (hkv-il-tunnel.service) exposes it to the job containers, which set
HKV_KNESSET_PROXY=http://172.18.0.1:8890. Only CONNECT to port 443 of knesset.gov.il hosts is allowed, so the
server cannot use this connection for anything else. Standard library only (works with Python 3.9+).
"""

from __future__ import annotations

import asyncio
import logging
import sys

LISTEN = ("127.0.0.1", 8890)
ALLOWED = ("knesset.gov.il",)          # the host itself and its subdomains
log = logging.getLogger("knesset_proxy")


def allowed(host: str, port: int) -> bool:
    host = host.lower().rstrip(".")
    return port == 443 and any(host == a or host.endswith("." + a) for a in ALLOWED)


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=30)
        method, target, _ = head.split(b"\r\n", 1)[0].decode("latin-1").split(" ", 2)
        host, _, port = target.rpartition(":")
        if method != "CONNECT" or not port.isdigit() or not allowed(host, int(port)):
            log.warning("refused %s %s", method, target)
            writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        up_reader, up_writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), timeout=30)
    except Exception as e:  # malformed request, timeout, upstream unreachable
        log.warning("failed: %r", e)
        try:
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
        except ConnectionError:
            pass
        writer.close()
        return
    writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
    await writer.drain()
    log.info("tunnel %s", target)
    await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))


async def main() -> None:
    server = await asyncio.start_server(handle, *LISTEN)
    log.info("listening on %s:%d, allowed: %s", *LISTEN, ", ".join(ALLOWED))
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
