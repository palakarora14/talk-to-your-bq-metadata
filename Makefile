.EXPORT_ALL_VARIABLES:

venv:
	# Install https://github.com/astral-sh/uv on macOS and Linux:
	# $ curl -LsSf https://astral.sh/uv/install.sh | sh
	uv sync

clean:
	rm -rf .venv

run:
	uv run hackday_45_talk_to_your_data "my required arg" --optional-arg "my optional arg"

test:
	uv run dev/test

manual-checks:
	uv run ruff format .
	uv run ruff check . --fix
	uv run pyright

precommit-install:
	# One time: Install git hook to run pre-commit automatically on git commit
	# Uninstall with: uv run pre-commit uninstall
	uv run pre-commit install

precommit:
	uv run pre-commit run --all-files

agent-skills-symlink:
	ln -s AGENTS.md CLAUDE.md
	ln -s ../.agents/skills ./.claude/skills
	ln -s ../.agents/skills ./.codex/skills

agent-skills-verify:
	ls -la CLAUDE.md
	ls -la ./.claude/skills ./.codex/skills

.DEFAULT_GOAL := help
.PHONY: help
help:
	@LC_ALL=C $(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'
