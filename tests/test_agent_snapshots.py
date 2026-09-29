import json
import threading

from src.agent.snapshots import (
    Snapshot,
    SnapshotStore,
    canonical_url,
    import_legacy_json,
    merge_duplicates,
)


def snap(job_id="1", content="<p>Build things</p>", fetched="2026-03-01T00:00:00+00:00", **kw):
    return Snapshot.create(
        source=kw.pop("source", "greenhouse"),
        source_job_id=job_id,
        raw_content=content,
        title=kw.pop("title", "Engineer"),
        location=kw.pop("location", "NYC"),
        fetched_at=fetched,
        **kw,
    )


def test_create_normalizes_text_and_hashes_content():
    s = snap()
    assert s.job_key == "greenhouse:1"
    assert s.text == "Build things"
    assert s.raw_content == "<p>Build things</p>"
    assert len(s.content_hash) == 64


def test_hash_depends_on_title_location_and_content():
    base = snap()
    assert snap().content_hash == base.content_hash
    assert snap(title="Other").content_hash != base.content_hash
    assert snap(location="SF").content_hash != base.content_hash
    assert snap(content="<p>Different</p>").content_hash != base.content_hash


def test_hash_ignores_fetch_time_and_hints():
    assert snap(fetched="2026-04-01T00:00:00+00:00", hints={"a": 1}).content_hash == snap().content_hash


def test_fetch_time_is_normalized_to_utc():
    s = snap(fetched="2026-03-01T09:00:00+09:00")
    assert s.fetched_at == "2026-03-01T00:00:00+00:00"


def test_put_new_then_same_content_only_refreshes_last_seen():
    store = SnapshotStore()
    r1 = store.put(snap())
    assert r1.is_new_version and r1.snapshot.version == 1
    r2 = store.put(snap(fetched="2026-03-05T00:00:00+00:00"))
    assert not r2.is_new_version
    assert r2.snapshot.version == 1
    assert r2.snapshot.fetched_at == "2026-03-01T00:00:00+00:00"
    assert r2.snapshot.last_seen_at == "2026-03-05T00:00:00+00:00"
    assert len(store.history("greenhouse:1")) == 1


def test_changed_content_creates_new_version_and_keeps_old():
    store = SnapshotStore()
    store.put(snap())
    r = store.put(snap(content="<p>Now with LLMs</p>", fetched="2026-03-10T00:00:00+00:00"))
    assert r.is_new_version and r.snapshot.version == 2
    assert r.previous_hash == snap().content_hash
    assert [h.text for h in store.history("greenhouse:1")] == ["Build things", "Now with LLMs"]


def test_older_last_seen_never_moves_backwards():
    store = SnapshotStore()
    store.put(snap(fetched="2026-03-05T00:00:00+00:00"))
    r = store.put(snap(fetched="2026-03-02T00:00:00+00:00"))
    assert r.snapshot.last_seen_at == "2026-03-05T00:00:00+00:00"


def test_latest_as_of_replays_old_version():
    store = SnapshotStore()
    store.put(snap(fetched="2026-03-01T00:00:00+00:00"))
    store.put(snap(content="<p>v2</p>", fetched="2026-03-10T00:00:00+00:00"))
    assert store.latest("greenhouse:1").text == "v2"
    assert store.latest("greenhouse:1", as_of="2026-03-05T00:00:00+00:00").text == "Build things"
    assert store.latest("greenhouse:1", as_of="2026-02-01T00:00:00+00:00") is None
    assert store.latest("missing") is None


def test_all_latest_and_as_of():
    store = SnapshotStore()
    store.put(snap("1", fetched="2026-03-01T00:00:00+00:00"))
    store.put(snap("1", content="<p>v2</p>", fetched="2026-03-10T00:00:00+00:00"))
    store.put(snap("2", fetched="2026-03-08T00:00:00+00:00"))
    now = {s.job_key: s.text for s in store.all_latest()}
    assert now == {"greenhouse:1": "v2", "greenhouse:2": "Build things"}
    then = {s.job_key: s.text for s in store.all_latest(as_of="2026-03-05T00:00:00+00:00")}
    assert then == {"greenhouse:1": "Build things"}
    assert store.count() == 2


def test_hints_roundtrip_through_storage():
    store = SnapshotStore()
    store.put(snap(hints={"tags": ["python"], "salary_min": None}))
    assert store.latest("greenhouse:1").hints == {"tags": ["python"], "salary_min": None}


def test_persists_to_disk(tmp_path):
    path = tmp_path / "snap.db"
    a = SnapshotStore(path)
    a.put(snap())
    a.close()
    b = SnapshotStore(path)
    assert b.latest("greenhouse:1").text == "Build things"


def test_concurrent_puts_do_not_corrupt_versions():
    store = SnapshotStore()

    def worker(i):
        store.put(snap("1", content=f"<p>content {i}</p>", fetched="2026-03-01T00:00:00+00:00"))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    versions = [h.version for h in store.history("greenhouse:1")]
    assert versions == list(range(1, 21))


def test_snapshot_segments_uses_normalized_text():
    s = snap(content="<p>Intro</p><h3>Responsibilities</h3><p>Build</p>")
    assert [x.kind for x in s.segments()] == ["intro", "responsibilities"]


def test_canonical_url():
    assert canonical_url("HTTPS://Jobs.Example.com/a/1/?utm=x#frag") == "https://jobs.example.com/a/1"
    assert canonical_url("") is None
    assert canonical_url(None) is None
    assert canonical_url("not a url") is None


def test_merge_duplicates_only_on_same_link():
    a = snap("1", url="https://x.com/j/1", fetched="2026-03-01T00:00:00+00:00")
    b = snap("2", source="lever", url="https://x.com/j/1/", fetched="2026-03-05T00:00:00+00:00")
    c = snap("3", url="https://x.com/j/2")
    d = snap("4")  # no link, same title/location as the others: must NOT merge
    reps, merged = merge_duplicates([a, b, c, d])
    assert sorted(r.job_key for r in reps) == ["greenhouse:3", "greenhouse:4", "lever:2"]
    assert merged == {"lever:2": ["greenhouse:1"]}


def test_import_legacy_json(tmp_path):
    records = [
        {"job_id": "gh_100", "source": "greenhouse", "company": "Figma", "title": "SWE", "location": "NYC",
         "remote": None, "salary_min": None, "salary_max": None, "publish_time": "2026-02-24T09:25:19-05:00",
         "tags": ["python"], "description": "<p>Build</p>"},
        {"job_id": "hn_7", "source": "hackernews", "company": "Acme", "title": "Backend", "location": "",
         "remote": True, "salary_min": 100, "salary_max": 200, "publish_time": None, "tags": [],
         "description": "Acme | Go"},
    ]
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps(records))
    store = SnapshotStore()
    assert import_legacy_json(path, store, fetched_at="2026-03-01T00:00:00+00:00") == 2
    gh = store.latest("greenhouse:100")
    assert gh.text == "Build" and gh.hints["legacy_job_id"] == "gh_100"
    hn = store.latest("hackernews:7")
    assert hn.hints["salary_min"] == 100 and hn.hints["remote"] is True
    # re-import is idempotent
    import_legacy_json(path, store, fetched_at="2026-03-02T00:00:00+00:00")
    assert len(store.history("greenhouse:100")) == 1
