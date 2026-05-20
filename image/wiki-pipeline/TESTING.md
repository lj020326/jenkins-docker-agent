
# Testing notes

## Test hash method used in the ./.wiki-state.json

```shell
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ sha256sum TODO.md 
f0b8882eba496117471bc88ac7389f96ccb6f5c8626f657ba593ae5c65505c8f  TODO.md
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ sha256sum docs/ansible/ansible-automation-platform/aap-cicd-gitlab-runner-ansible.md
face69985a7b3c1c4b2e462c0c5e18821b31781f1c8499dd2fd42e38078bc3d1  docs/ansible/ansible-automation-platform/aap-cicd-gitlab-runner-ansible.md
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ sha256sum TESTING.md 
2dec12143a1ea6eea66b9f0c3e58009c1a44ec5c0988731e1a0ae30b8ec176ac  TESTING.md
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ python3 -c "import hashlib; from pathlib import Path; print(hashlib.sha256(Path('TESTING.md').read_bytes()).hexdigest())"
2dec12143a1ea6eea66b9f0c3e58009c1a44ec5c0988731e1a0ae30b8ec176ac
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ python3 -c "import hashlib; from pathlib import Path; print(hashlib.sha256(Path('TODO.md').read_bytes()).hexdigest())"
f0b8882eba496117471bc88ac7389f96ccb6f5c8626f657ba593ae5c65505c8f
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$
```

## A Note on Directories

If you are trying to hash a directory (like an Ansible role) to match the get_content_fingerprint output, a one-liner becomes too complex. In that case, it is better to call your utils.py directly:

```shell
ljohnson@lees-mbp:[ansible-datacenter](develop-lj)$ python3 -c "from scripts.utils import get_content_fingerprint; from pathlib import
```
