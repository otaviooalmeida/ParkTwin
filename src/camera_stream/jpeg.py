from __future__ import annotations

import html
import re
from pathlib import Path
from time import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; ParkTwin/1.0)"
_IMAGE_URL_PATTERN = re.compile(
    r"imageurls\[\d+\]\s*=\s*(?:new\s+String\()?['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_IMAGE_SRC_PATTERN = re.compile(
    r"<img\b[^>]*\bid=['\"]image\d+['\"][^>]*\bsrc=['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def discover_insecam_snapshot_url(
    page_url: str,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    html_text = _fetch_text(page_url, timeout=timeout, user_agent=user_agent)

    for pattern in (_IMAGE_URL_PATTERN, _IMAGE_SRC_PATTERN):
        match = pattern.search(html_text)
        if match is not None:
            return html.unescape(match.group(1))

    raise ValueError(f"Could not find a JPEG snapshot URL in {page_url}")


def build_frame_url(
    snapshot_url: str,
    counter: int | None = None,
    channel: int | None = None,
) -> str:
    cache_buster = counter if counter is not None else int(time() * 1000)
    frame_url = snapshot_url.replace("COUNTER", str(cache_buster))

    if channel is not None:
        frame_url = frame_url.replace("CHANNEL", str(channel))

    if "COUNTER" in snapshot_url:
        return frame_url

    return _append_query_param(frame_url, "_parktwin_ts", str(cache_buster))


def fetch_jpeg_frame(
    snapshot_url: str,
    output_path: str | Path,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_USER_AGENT,
    counter: int | None = None,
    channel: int | None = None,
) -> Path:
    frame_url = build_frame_url(snapshot_url, counter=counter, channel=channel)
    request = Request(frame_url, headers={"User-Agent": user_agent})

    with urlopen(request, timeout=timeout) as response:
        content = response.read()

    if not content.startswith(b"\xff\xd8"):
        raise ValueError(f"Response is not a JPEG frame: {frame_url}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(content)
    temp_path.replace(path)
    return path


def _fetch_text(url: str, timeout: float, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent})

    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _append_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    query_params.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(query_params)))
