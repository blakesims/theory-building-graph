.PHONY: test acceptance baseline serve check

test:
	python3 -m unittest discover -s . -p 'test*.py' -v

acceptance:
	python3 acceptance/validate_suite.py
	python3 acceptance/run.py

baseline:
	python3 acceptance/baseline_smoke.py --engine .

serve:
	python3 graph.py serve --port 8767

check:
	./tg check
