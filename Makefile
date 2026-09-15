.PHONY: test acceptance baseline serve check

test:
	python3 -m unittest discover -s tests -t . -p 'test*.py' -v

acceptance:
	python3 acceptance/validate_suite.py
	python3 acceptance/run.py

baseline:
	python3 acceptance/baseline_smoke.py --engine .

serve:
	./tg -p morphisms serve --port 8767

check:
	./tg -p morphisms check
