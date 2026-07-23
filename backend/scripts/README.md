# Live smoke scripts

Automated tests live in `backend/tests`. Scripts here validate running services
and can consume provider quota.

```bash
python scripts/test_sandbox.py
python scripts/test_full_stack.py
python scripts/test_vectorstore.py
python scripts/test_nodes.py
python scripts/test_stream.py
```

`test_sandbox.py` needs Docker. Vector, node, and stream checks need matching
environment configuration. See `docs/Configuration.md`.
