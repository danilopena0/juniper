import os
import sys

from juniper.fetch import (
    delta_pipeline,
    eei_pipeline,
    legiscan_pipeline,
    puc_rss_pipeline,
)
from juniper.render import digest


def main() -> None:
    api_key = os.environ.get("LEGISCAN_API_KEY", "")
    if not api_key:
        print(
            "run_weekly: LEGISCAN_API_KEY not set, legiscan lane will fail closed",
            file=sys.stderr,
        )

    lanes = [
        ("legiscan", lambda: legiscan_pipeline.run(api_key=api_key)),
        ("puc_rss", puc_rss_pipeline.run),
        ("eei_pdf", eei_pipeline.run),
        ("delta_db", delta_pipeline.run),
    ]
    for name, fn in lanes:
        try:
            fn()
        except Exception as exc:
            print(
                f"run_weekly: {name} pipeline crashed unexpectedly, skipping: {exc}",
                file=sys.stderr,
            )

    digest.run()


if __name__ == "__main__":
    main()
