# TODO — crewai-doc-agent

## Done (ansible-focused path)
- [x] Real Python package layout (`crewai_doc_agent`)
- [x] Config load + LLM healthcheck (Basic auth / Ollama)
- [x] Local LanceDB memory under `.agent_state/crewai` + Ollama embedder
- [x] Hierarchical packaging thresholds (`oversized_directories` + re-package hints)
- [x] Role-first crew → inventory/playbooks → root
- [x] Wiki writers → `wiki/roles/<name>.md`, `wiki/architecture/overview.md`
- [x] `changedOnly` / `CREWAI_MAX_ROLES` for CI smoke vs full scans

## Near-term
- [ ] Persist unit reviews for `inventory/`, `playbooks/` consistently
- [ ] `changedOnly` for non-role paths (playbooks, plugins)
- [ ] Optional: only rewrite wiki pages when package hash changes
- [ ] Guardrail: fail task if Write Wiki Document was not called

## Multi-language / multi-repo-type support
Goal: same pipeline image works on heterogeneous repos with auto detection.

### Detection (`detect_repo_type`)

| Type               | Signals                                                    |
|--------------------|------------------------------------------------------------|
| `ansible-playbook` | `roles/` + (`playbooks/` \| `ansible.cfg` \| `inventory/`) |
| `ansible-plugins`  | `plugins/` + (`galaxy.yml` \| collection `meta/`)          |
| `python`           | `pyproject.toml` \| `setup.py` \| `src/` + packages        |
| `java`             | `pom.xml` \| `build.gradle`                                |
| `rust`             | `Cargo.toml`                                               |
| `golang`           | `go.mod`                                                   |
| `generic`          | fallback: package root + oversized-dir drill-down only     |

### Generic strategy (when no specialized handlers)
1. Top-level `package_dir` with oversized thresholds
2. For each entry in `__meta__.oversized_directories`, spawn package+review tasks
3. Write `wiki/modules/<name>.md` or language-idiomatic paths
4. Root architecture page last (memory-aware)

### Specialized handlers to implement
- [ ] **python**: package per top-level module under `src/` or package dirs; wiki under `wiki/modules/`
- [ ] **java**: package per Maven/Gradle module
- [ ] **rust**: package per workspace crate
- [ ] **golang**: package per major package dir under module root
- [ ] **ansible-plugins**: package `plugins/modules`, `plugins/filter`, etc.

### Pipeline
- [ ] Auto-set `CREWAI_REPO_TYPE` from detection (override via param)
- [ ] Language-specific `maxUnits` analogous to `maxRoles`
- [ ] Matrix note in README: one image, many repo types

## Ops / quality
- [ ] Integration test: fixture ansible tree → assert wiki files exist
- [ ] Integration test: oversized `roles/` summary without full inline
- [ ] Document embedder Basic-auth behavior against Ollama `/v1/embeddings`
