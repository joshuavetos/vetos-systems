install:
	pip install -r requirements.txt

verify:
	pytest -q
	python artifacts/epistemic-instruments/semantic_auditor_v3_3.py --input-csv samples/sample_support_tickets.csv --text-column text
	python tools/funding-analysis/audit_pipeline.py --input-json samples/sample_funding_payload.json
	FAILURE_ORACLE_SEED=2026 FAILURE_ORACLE_SKIP_DOCKER=1 python work-samples/failure_oracle.py --artifact-path work-samples/failure_oracle.c --output-json /tmp/failure_oracle_output.json
	python -c "from pathlib import Path; import json; expected=json.loads(Path('samples/sample_failure_oracle_output.json').read_text()); actual=json.loads(Path('/tmp/failure_oracle_output.json').read_text()); assert expected==actual, 'failure oracle output mismatch'; print('failure oracle output matches committed artifact')"

run:
	python tools/funding-analysis/allocation_extraction.py
