.PHONY: test acceptance baseline serve check

test:
	python3 -m unittest discover -s tests -t . -p 'test*.py' -v
	$(MAKE) acceptance

acceptance:
	python3 -m tests.acceptance.validate_suite
	python3 -m tests.acceptance.run --report /tmp/theorygraph-acceptance-report.json

baseline:
	python3 -m tests.acceptance.baseline_smoke --engine .

serve:
	./tg -p morphisms serve --port 8767

check:
	./tg -p morphisms check
