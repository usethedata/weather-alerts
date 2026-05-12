# Description
Project-specific to-do items for weather-tools (GitHub: usethedata/weather-tools). High-level cross-project items live in `BEWMain/Progs/TODO.md`.

## Items

- [ ] Rename `check-weather-collect` to something more meaningful.
    The current name is generic. A name along the lines of `get-weather-forecasts-actuals` describes what the script actually does (retrieves the forecast and yesterday's actuals from NWS and writes them to the archive). Any rename must also update the systemd service unit in chezmoi (`dot_config/systemd/user/weather-collect.service`: `ExecStart`), the `$LOG_DIR` filename pattern in the wrapper, any `~/bin` symlinks created by `install.sh`, and references in `README.md`, `CLAUDE.md`, and `TODO.md`. Consider renaming `check-weather-alerts` at the same time for consistency.

- [ ] Harden NWS forecast fetch against transient timeouts.
    `src/weather/forecast.py` makes two sequential NWS API calls (`/points/{lat,lon}` then the `forecast` URL), both with a hard 10-second timeout and no retry logic. Either call timing out kills the whole forecast. Observed to fail at 05:00 EDT on 2026-04-21 (last macOS run before the migration to the Linux system) and 2026-04-22 (the first automated run on the Linux system); a manual rerun at 09:09 on 2026-04-22 succeeded, so the endpoint is reachable but slow/flaky at 05:00. Fix: add retries with exponential backoff and a longer connect/read timeout; consider caching the points→gridpoint URL mapping so successful first calls don't have to repeat on retry. Actuals collection has no such issue.

- [ ] Add log-to-file handling in `check-weather-alerts`, matching `check-weather-collect`.
    Currently `check-weather-collect` honors `$LOG_DIR` and writes a timestamped log file when set. `check-weather-alerts` does not — it just execs the Python process. When alerts move to a scheduled run (see "unified daily job" in `CLAUDE.md` Future Plans), logging will matter. Pattern to copy is the existing `LOG_DIR` block in `check-weather-collect`.

- [ ] Relocate the alert state file to the XDG state location.
    Currently at `~/.weather_alerts_state.json` (legacy). XDG-compliant location is `~/.local/state/weather-tools/alerts_state.json`. Requires a `config.yaml` edit on each host and a one-time `mv` of the existing file. Low priority — the current location works.

- [ ] Reconsider whether SMTP credentials belong in Dropbox-synced `config.yaml`.
    `config.yaml` is gitignored but Dropbox-synced, so the Fastmail SMTP password ends up on every host that syncs BEWMain (including synologies). Current threat model accepts this for convenience. Alternatives: split secrets into a non-Dropbox file (`~/.config/weather-tools/secrets.yaml` or env vars), or accept the status quo and document the decision. Decide when the broader "machine-specific files out of Dropbox" refactor runs across projects.

