# DELTa manual drop-in

`sepapower.org`'s DELTa database (Database of Emerging Large-Load Tariffs)
can't be fetched automatically: the site sits behind a Cloudflare
JS/Turnstile challenge, and even past that, the export is distributed
through an email-gated download form rather than served as a plain file.
See `ROADMAP.md` for the full writeup.

## What to do

1. Go to <https://sepapower.org/large-load-tariffs-database/> and download
   the current export (requires providing an email address on their form).
2. Drop the downloaded file in this directory. Any format is fine — the
   pipeline hashes it as opaque bytes, it doesn't need to be a specific
   file type.
3. Run `uv run python -m juniper.fetch.delta_pipeline` (or let the weekly
   pipeline pick it up on its next run, once that's wired).

The pipeline picks up whichever file in this directory has the most
recent modification time, so you can just drop a new export in when
NCCETC publishes one (roughly quarterly) — no need to delete the old one
first, though it's fine to.

## Do not automate the download

The email-gated form and Cloudflare challenge are both signals that this
resource isn't meant for unattended automated access. Don't script around
either of them — this manual step is a deliberate design choice, not a
gap to be closed later.
