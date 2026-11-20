.PHONY: run init test lint scheduler
run:
	python3 run.py
init:
	python3 run.py --init
test:
	python3 run.py --init
	.venv/bin/python -m pytest -q
lint:
	.venv/bin/ruff check --select E9,F63,F7,F82 backend collectors registries tests
scheduler:
	python3 run.py --scheduler
