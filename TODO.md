# Description
Project-specific to-do items for weather-tools (GitHub: usethedata/weather-tools). High-level cross-project items live in `BEWMain/Progs/TODO.md`.

## Items

- [ ] Rename `check-weather-collect` to something more meaningful.
    The current name is generic. A name along the lines of `get-weather-forecasts-actuals` describes what the script actually does (retrieves the forecast and yesterday's actuals from NWS and writes them to the archive). Any rename must also update the systemd service unit in chezmoi (`dot_config/systemd/user/weather-collect.service`: `ExecStart`), the `$LOG_DIR` filename pattern in the wrapper, any `~/bin` symlinks created by `install.sh`, and references in `README.md`, `CLAUDE.md`, and `TODO.md`. Consider renaming `check-weather-alerts` at the same time for consistency.

- [ ] Persist the NWS points→gridpoint URL cache across runs.
    `src/weather/forecast.py` now caches the `/points/{lat,lon}` → forecast URL mapping in memory for the lifetime of a `WeatherForecast` instance, but each scheduled run starts fresh and still has to make the points call. The mapping is effectively static for a fixed location, so a small on-disk cache (e.g., `~/.cache/weather-tools/nws-points.json`, with an occasional refresh) would let routine runs skip the points call entirely and only hit the forecast URL. Hold off until we see whether the retry + in-memory cache work (added 2026-05-12) is enough to eliminate the 05:00 failures on its own.

- [ ] Add log-to-file handling in `check-weather-alerts`, matching `check-weather-collect`.
    Currently `check-weather-collect` honors `$LOG_DIR` and writes a timestamped log file when set. `check-weather-alerts` does not — it just execs the Python process. When alerts move to a scheduled run (see "unified daily job" in `CLAUDE.md` Future Plans), logging will matter. Pattern to copy is the existing `LOG_DIR` block in `check-weather-collect`.

- [ ] Relocate the alert state file to the XDG state location.
    Currently at `~/.weather_alerts_state.json` (legacy). XDG-compliant location is `~/.local/state/weather-tools/alerts_state.json`. Requires a `config.yaml` edit on each host and a one-time `mv` of the existing file. Low priority — the current location works.

- [ ] Reconsider whether SMTP credentials belong in Dropbox-synced `config.yaml`.
    `config.yaml` is gitignored but Dropbox-synced, so the Fastmail SMTP password ends up on every host that syncs BEWMain (including synologies). Current threat model accepts this for convenience. Alternatives: split secrets into a non-Dropbox file (`~/.config/weather-tools/secrets.yaml` or env vars), or accept the status quo and document the decision. Decide when the broader "machine-specific files out of Dropbox" refactor runs across projects.

