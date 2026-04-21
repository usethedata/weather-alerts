# Description
Project-specific to-do items for weather-tools (GitHub: usethedata/weather-tools). High-level cross-project items live in `BEWMain/Progs/TODO.md`.

## Items

- [ ] Add log-to-file handling in `check-weather-alerts`, matching `check-weather-collect`.
    Currently `check-weather-collect` honors `$LOG_DIR` and writes a timestamped log file when set. `check-weather-alerts` does not — it just execs the Python process. When alerts move to a scheduled run (see "unified daily job" in `CLAUDE.md` Future Plans), logging will matter. Pattern to copy is the existing `LOG_DIR` block in `check-weather-collect`.

- [ ] Relocate the alert state file to the XDG state location.
    Currently at `~/.weather_alerts_state.json` (legacy). XDG-compliant location is `~/.local/state/weather-tools/alerts_state.json`. Requires a `config.yaml` edit on each host and a one-time `mv` of the existing file. Low priority — the current location works.

- [ ] Reconsider whether SMTP credentials belong in Dropbox-synced `config.yaml`.
    `config.yaml` is gitignored but Dropbox-synced, so the Fastmail SMTP password ends up on every host that syncs BEWMain (including synologies). Current threat model accepts this for convenience. Alternatives: split secrets into a non-Dropbox file (`~/.config/weather-tools/secrets.yaml` or env vars), or accept the status quo and document the decision. Decide when the broader "machine-specific files out of Dropbox" refactor runs across projects.
