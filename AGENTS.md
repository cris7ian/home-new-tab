# Home New Tab

- Run `python3 experiments/build_globe.py` to build `extension/` and local previews. `experiments/preview-local/globe.html` is the web artifact. The ignored `public/` directory is served live; never overwrite it during a preview build.
- Test with `uv run --with playwright python experiments/verify_globe.py --chromium /path/to/chromium` while the documented loopback preview server runs. Test the actual `chrome://newtab/` override, not only the web preview.
- Chrome rejects `geolocation` under `optional_permissions`. Keep it under `permissions`, but gate device readings on the user's in-app opt-in. Keep the permission disclosure and public privacy policy aligned.
- Keep the manual install ZIP (`extension/` wrapper) and Chrome Web Store ZIP (root `manifest.json`) separate. A GitHub release does not submit a Store update.
- On production-server, test the web artifact before atomically replacing `public/index.html`. Check served bytes over public HTTPS after deploying. Publish `experiments/store/privacy.html` at `/privacy.html` when privacy behavior changes.
