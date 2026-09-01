from camera_stream.jpeg import build_frame_url, discover_insecam_snapshot_url


def test_build_frame_url_replaces_insecam_counter_placeholder():
    snapshot_url = "http://example.test/webcapture.jpg?command=snap&channel=1?COUNTER"

    frame_url = build_frame_url(snapshot_url, counter=123)

    assert frame_url == "http://example.test/webcapture.jpg?command=snap&channel=1?123"


def test_build_frame_url_appends_cache_buster_when_no_placeholder():
    frame_url = build_frame_url(
        "http://example.test/snapshot.jpg?quality=80",
        counter=123,
    )

    assert frame_url == "http://example.test/snapshot.jpg?quality=80&_parktwin_ts=123"


def test_discover_insecam_snapshot_url_from_imageurls(monkeypatch):
    html = """
    <script>
    imageurls[0] = new String("http://example.test/snapshot.jpg?COUNTER");
    </script>
    """

    monkeypatch.setattr("camera_stream.jpeg._fetch_text", lambda *args, **kwargs: html)

    assert (
        discover_insecam_snapshot_url("http://www.insecam.org/en/view/945438/")
        == "http://example.test/snapshot.jpg?COUNTER"
    )


def test_discover_insecam_snapshot_url_decodes_html_entities(monkeypatch):
    html = """
    <img id="image0" src="http://example.test/snapshot.jpg?x=1&amp;COUNTER" />
    """

    monkeypatch.setattr("camera_stream.jpeg._fetch_text", lambda *args, **kwargs: html)

    assert (
        discover_insecam_snapshot_url("http://www.insecam.org/en/view/945438/")
        == "http://example.test/snapshot.jpg?x=1&COUNTER"
    )
