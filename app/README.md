# EdgeIMCI prototype application

This application layer connects the fixture-based extraction prototype to the
existing deterministic clinical engine and the React worker interface.

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

The current extractor recognizes only the five approved fixture submissions.
It does not run a language model or interpret arbitrary clinical text.
