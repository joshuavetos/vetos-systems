install:
	pip install -r requirements.txt

test:
	python -m compileall -q .
	python work-samples/failure_oracle.py
	python -c "import importlib.util; spec=importlib.util.spec_from_file_location('funding_audit', 'tools/funding-analysis/audit_pipeline.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); payload=[{'project_name':'Test','budget_allocation':1000.0,'fiscal_start':2025,'fiscal_end':2026},{'project_name':'Edge','budget_allocation':1005.0,'fiscal_start':2025,'fiscal_end':2027},{'project_name':'Outlier','budget_allocation':50000.0,'fiscal_start':2025,'fiscal_end':2028},{'project_name':'Steady','budget_allocation':1002.0,'fiscal_start':2025,'fiscal_end':2026},{'project_name':'Normal','budget_allocation':1003.0,'fiscal_start':2025,'fiscal_end':2027}]; result=mod.run_financial_audit(payload); print(result['status'], result.get('records_validated', 0), result.get('records_rejected', 0))"

run:
	python tools/funding-analysis/allocation_extraction.py
