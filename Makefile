install:
	pip install -r requirements.txt

test:
	pytest -q

run:
	python tools/funding-analysis/allocation_extraction.py
