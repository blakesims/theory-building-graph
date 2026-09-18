.PHONY: test browser-smoke serve check

test:
	python3 -m unittest discover -s tests -t . -p 'test*.py' -v

# Live viewer check in a real browser; needs Node (npx agent-browser). Not part of `make test`.
browser-smoke:
	python3 -m tests.acceptance.browser_smoke

serve:
	./tg -p morphisms serve --port 8767

check:
	./tg -p morphisms check
