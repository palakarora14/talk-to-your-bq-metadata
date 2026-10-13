# chroma_db/

This directory is populated by the ingestion pipeline (`auto/run-local`) and mounted read-only into the UI container by `auto/start-ui-app`.

**Do not commit Chroma data files** — only `.gitkeep` and this README are tracked.

To populate locally:
```bash
./auto/run-local   # runs BQ → embed → write Chroma (once ingestion code is merged)
```
