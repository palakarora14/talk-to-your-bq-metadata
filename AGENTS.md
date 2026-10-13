# AGENTS Guidelines

This file contains guidelines for AI agents to follow when writing code in this project.

## `hackday_45_talk_to_your_data` project vision

NOTE: this project is a WIP, this vision is under active development.

TODO: add project vision, goals, and non-goals here to guide AI agents in development.

## Simplicity First Guidelines

- Before implementing: if requirements are ambiguous, ask first.
- Write simple, clean, maintainable, minimal code.
- Don't over complicate or over engineer solutions.
- If you write 200 lines and it could be 50, rewrite it.
- No error handling for impossible scenarios.
- No "flexibility" or "configurability" that wasn't requested.
- Chat style: Always be extremely concise. Sacrifice grammar for the sake of being concise. Skip preamble and recaps.
- Self-check before finishing: "Would a senior engineer call this overcomplicated?" If yes, simplify.

## Python Coding Guidelines

- Keep docstrings minimal, prefer the code to speak for itself.
- Keep functions focused on a single responsibility.
- Don't create unnecessary small wrapper functions, prefer inlining.
- Use asserts to check assumptions when appropriate.
- Use type hints for all function parameters and return values.
- Keep sensitive information in `.env` files.
- Provide meaningful error messages.
- Leverage `async` and `await` for I/O-bound operations to maximize concurrency.
- Leverage `asyncio` as an event-loop framework when appropriate.
- Use caching like `@functools.cache`, or `@functools.lru_cache`, when appropriate.
- Use f-strings for string formatting, and use the f"{var=}" syntax to show the variable name and its value.
- A functional programming approach is preferred over an object-oriented one. Use classes when appropriate.
- Use Pydantic data models when appropriate.
- Target Python version is specified in `pyproject.toml`.

## Test-Driven Development (TDD) Guidelines

- Follow the red-green-refactor loop when appropriate. Write one failing test (RED), minimal code to pass it (GREEN), then refactor—repeat.
- Test behaviour, not implementation. Write integration-style tests against public APIs that read like specs ("user can checkout with valid cart") and describe _what_ the system does, not _how_. These survive refactors; if renaming an internal function breaks a test, that test was wrong. Avoid bad tests coupled to implementation—mocking internal collaborators, testing private methods, or verifying through external means.
- Go vertical, never horizontal. One test → one implementation → repeat. Never write all tests first—that tests imagined behaviour and data shapes instead of real, user-facing behaviour.
- Plan before coding. Focus testing effort on critical paths and complex logic, not every possible edge case.
- Refactor only when GREEN. Once tests pass, remove duplication and hide complexity behind simple interfaces, re-running tests after each step. No speculative features, and never refactor while RED.

## Critical Thinking

- Fix root cause (not band-aid).
- If you are unsure: read more code; if still stuck, ask with short options.
- Prefer correct, maintainable implementations over clever, complex ones.
- If a popular, well tested library exists for a task, use it instead of reinventing the wheel.
- Be careful with secrets - do not expose them to the world (e.g. in logs, comments, git, etc.).

## Project Structure

- Keep source code in a `./src/hackday_45_talk_to_your_data/` directory.
- Place tests in a `./tests/hackday_45_talk_to_your_data/` directory.
- Keep configuration files in the root directory.

## Package Management with uv

- Package management is via `uv`.
- Create venv and install deps with `uv sync`.
- Manage dependencies via `pyproject.toml`, with dev dependencies in the `[dependency-groups]` section.
- Add runtime dependencies: `uv add <pkg>`.
- Add dev dependencies: `uv add --group dev <pkg>`.
- Sync lockfile: `uv sync`.

## Tests

- Use `pytest` for testing.
- Use `pytest-cov` for code coverage reporting.
- Follow the naming convention: `test_*.py`.
- Use fixtures for test setup and teardown.
- Place test files in `./tests/hackday_45_talk_to_your_data/`.
- Run the tests with `uv run pytest`

## Linting

- Use `ruff` for formatting and linting.
- Run `uv run ruff format .` to format the code.
- Run `uv run ruff check . --fix` to check the code and fix any issues.

## Type Checking

- Use `pyright` for type checking.
- Run `uv run pyright` to type check the code.
