# Testing & Verification Notes for CrewAI Documentation Agent

## Verifying LLMClient Connection & Health Check

The `LLMClient` performs an automatic connection health check on initialization. You can test connectivity and authentication against your local or remote Ollama/vLLM backend directly via Python:

```python
python3 -c "
from scripts.utils import LLMClient
try:
    client = LLMClient(config_path='.crewai-config.yml')
    print('SUCCESS: Connected to LLM endpoint successfully.')
except Exception as e:
    print(f'FAILED: {e}')
"
```

## Validating Basic Authentication Headers

When utilizing an Ollama endpoint protected by HTTP Basic Auth, verify that your credentials (`username:password` or encoded token) properly populate `extra_headers`:

```python
python3 -c "
import base64
api_key = 'admin:secretpassword'
encoded_bytes = base64.b64encode(api_key.encode('utf-8'))
print(f'Authorization: Basic {encoded_bytes.decode(\"utf-8\")}')
"
```

## Testing Repository Context Packaging

To test the file scanner and ensure ignored patterns (like `.git`, `venv`, and binary files) are properly excluded before handing off to CrewAI:

```bash
python3 scripts/package_dir.py . --output save/test_context.yaml
head -n 20 save/test_context.yaml
```
