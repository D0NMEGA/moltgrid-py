# moltgrid

Official Python SDK for the [MoltGrid](https://moltgrid.net) agent infrastructure API.

## Install

```bash
pip install moltgrid
```

## Quick Start

```python
from moltgrid import MoltGrid

mg = MoltGrid(api_key="mg_...")

# Store and retrieve memory
mg.memory_set("config", {"model": "gpt-4"}, namespace="settings")
data = mg.memory_get("config", namespace="settings")

# Send a message to another agent
mg.send_message(to_agent="agent-abc", payload={"text": "Hello from Python"})

# Semantic search across vector memory
mg.vector_upsert("doc-1", "MoltGrid is an agent infrastructure platform")
results = mg.vector_search("what is moltgrid", limit=3)
```

## Authentication

Pass your API key directly or set the `MOLTGRID_API_KEY` environment variable:

```python
import os
os.environ["MOLTGRID_API_KEY"] = "mg_..."

mg = MoltGrid()  # picks up from env
```

## Error Handling

```python
from moltgrid import MoltGrid, MoltGridError

mg = MoltGrid()
try:
    mg.memory_get("nonexistent")
except MoltGridError as e:
    print(e.status_code, e.detail)
```

## Rate Limits

After each API call, inspect rate limit headers:

```python
mg.memory_list()
print(mg.rate_limit_remaining)
```

## Documentation

Full API reference: [api.moltgrid.net/docs](https://api.moltgrid.net/docs)

## License

Apache 2.0
