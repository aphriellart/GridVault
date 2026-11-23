# Contributing to GridVault

Thanks for helping! Bug reports, fixes, docs and translations are all welcome.

## Reporting a bug

Instagram's web app changes often, so the most useful report includes:

- what you ran (`__ig.start({...})` options, or the Python command)
- the `[GridVault]` lines from the browser Console, or the script output
- the result of `__ig.status()` if the collector stopped early
- browser + OS, and roughly how many posts the profile has

**Never paste cookies, session files, or `sessionid` values into an issue.**

## Pull requests

- Keep the browser collector dependency-free and readable: people paste it into their
  Console, so it must stay short enough to review.
- The collector should only read responses the page itself receives. Please don't add
  direct calls to Instagram's private APIs; they are what gets accounts blocked.
- `download_manifest.py` must keep working with the Python standard library only.
- Test against at least one real profile and mention the post count in the PR.

## Translations

Add a `README.<lang>.md` next to the others and link it from the language bar at the top
of each README.
