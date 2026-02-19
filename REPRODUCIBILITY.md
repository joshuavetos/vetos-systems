Clean-room reproducibility is the ability to execute a repository from a zero-state environment without hidden dependencies.

This repository has been validated from fresh Linux environments using:

- WSL Ubuntu
- Python 3.12
- Virtualenv isolation (PEP 668 compliant)

During clean execution, dependencies were discovered empirically and converged to the minimal runtime set.

Execution proofs are stored under artifacts/execution-proofs/.

Each proof contains environment fingerprints and raw test output.

To reproduce from zero:

1. Install Ubuntu or WSL
2. Install Python 3 and python3-venv
3. Create a virtual environment
4. Install requirements.txt
5. Run pytest

The goal is transparency of execution, not marketing claims.
