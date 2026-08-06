import juniper.run_weekly as run_weekly


def test_all_lanes_and_digest_are_called_once(monkeypatch):
    calls = []

    def legiscan_run(api_key):
        calls.append(("legiscan", api_key))

    monkeypatch.setattr(run_weekly.legiscan_pipeline, "run", legiscan_run)
    monkeypatch.setattr(
        run_weekly.puc_rss_pipeline, "run", lambda: calls.append(("puc_rss",))
    )
    monkeypatch.setattr(
        run_weekly.eei_pipeline, "run", lambda: calls.append(("eei_pdf",))
    )
    monkeypatch.setattr(
        run_weekly.delta_pipeline, "run", lambda: calls.append(("delta_db",))
    )
    monkeypatch.setattr(run_weekly.digest, "run", lambda: calls.append(("digest",)))
    monkeypatch.setenv("LEGISCAN_API_KEY", "test-key")

    run_weekly.main()

    names = [c[0] for c in calls]
    assert names == ["legiscan", "puc_rss", "eei_pdf", "delta_db", "digest"]
    assert calls[0] == ("legiscan", "test-key")


def test_missing_api_key_does_not_raise(monkeypatch):
    calls = []
    monkeypatch.setattr(
        run_weekly.legiscan_pipeline, "run", lambda api_key: calls.append(api_key)
    )
    monkeypatch.setattr(run_weekly.puc_rss_pipeline, "run", lambda: None)
    monkeypatch.setattr(run_weekly.eei_pipeline, "run", lambda: None)
    monkeypatch.setattr(run_weekly.delta_pipeline, "run", lambda: None)
    monkeypatch.setattr(run_weekly.digest, "run", lambda: None)
    monkeypatch.delenv("LEGISCAN_API_KEY", raising=False)

    run_weekly.main()

    assert calls == [""]


def test_one_lane_crashing_does_not_stop_the_others(monkeypatch):
    calls = []

    def boom(**kwargs):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(run_weekly.legiscan_pipeline, "run", lambda api_key: boom())
    monkeypatch.setattr(
        run_weekly.puc_rss_pipeline, "run", lambda: calls.append("puc_rss")
    )
    monkeypatch.setattr(run_weekly.eei_pipeline, "run", lambda: calls.append("eei_pdf"))
    monkeypatch.setattr(
        run_weekly.delta_pipeline, "run", lambda: calls.append("delta_db")
    )
    monkeypatch.setattr(run_weekly.digest, "run", lambda: calls.append("digest"))
    monkeypatch.setenv("LEGISCAN_API_KEY", "test-key")

    run_weekly.main()

    assert calls == ["puc_rss", "eei_pdf", "delta_db", "digest"]
