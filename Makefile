install:
	pip install -r requirements.txt

verify:
	python verify.py

run:
	python tools/funding-analysis/allocation_extraction.py
