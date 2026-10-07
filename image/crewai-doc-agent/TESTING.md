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

## Testing Repository Context Packaging Tool

To test the directory packaging script directly and inspect the rich metadata block (`__meta__`) including git commit hash, branch, execution PWD, and directory tree:

```bash
python3 scripts/package_dir.py .
head -n 25 .package_dir.context.yml
```

## Testing Modular Multi-Agent Crew Execution

To test the modular `run_crew()` function directly from Python:

```python
python3 -c "
from crewai import LLM
from scripts.utils import LLMClient
from scripts.crew import run_crew

llm_client = LLMClient(config_path='.crewai-config.yml')
llm = LLM(model=f'{llm_client.provider}/{llm_client.model}', base_url=llm_client.api_base)

result = run_crew(llm=llm, verbose=True)
print(result)
"
```
