# EdgeIMCI prototype application

This application layer connects either the offline fixture extractor or the
selected Qwen3-0.6B Modal checkpoint to the deterministic clinical engine and
React worker interface.

## Production-style local run

Build the frontend once, then serve the API and static bundle together:

```bash
cd web
npm install
npm run build
cd ..
PYTHONPATH="src:." python -m app
```

Open `http://127.0.0.1:8000`.

The application CLI defaults to the selected Modal checkpoint. Deploy the
pinned function once, then start the workstation:

```bash
uv run --extra modal-training modal deploy \
  -m edge_imci.inference.modal_structured_extraction
uv run --extra modal-training python -m app
```

The browser never receives Modal credentials. The backend accepts model output
only when the run ID, weights checksum, JSON parse, and model-facing schema all
match the selected candidate, then reruns the authoritative deterministic
adapter, evaluator, and approved response renderer locally.

## Frontend development

Run the Python service and Vite server in separate terminals from the repository
root:

```bash
PYTHONPATH="src:." python -m app
```

```bash
cd web
npm install
npm run dev
```

Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Verification

```bash
PYTHONPATH="src:." python -m pytest tests/test_prototype_app.py
cd web
npm test
npm run build
```

Stub mode recognizes only the five frozen fixture submissions. Modal mode sends
free-form findings to the provisionally selected research checkpoint. Neither
mode is authorized for production clinical use.

Use `--extractor stub` for deterministic offline UI development.
