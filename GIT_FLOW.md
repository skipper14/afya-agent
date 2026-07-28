# AfyaPlus Git Flow and Code Quality Guidelines

## Branch strategy
- Use `main` for production-ready code only.
- Create feature branches from `main` with descriptive names, for example:
  - `feat/rag-agent-system`
  - `fix/privacy-masking`
  - `docs/architecture`
- Keep feature branches isolated and focused on a single concern.

## Commit conventions
- Use semantic commit prefixes:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `refactor:` for internal cleanup
  - `test:` for test additions or updates
- Write concise commit messages that explain the what and why.

## Pull request checklist
- [ ] Code changes are limited to the feature scope.
- [ ] Updated or added tests for new behavior.
- [ ] Documentation updated when architecture or behavior changed.
- [ ] Security and privacy implications reviewed.
- [ ] Dependencies and environment changes recorded in `requirements.txt`.
- [ ] Confirm the branch can be merged cleanly into `main`.

## Review expectations
- Reviewers should verify:
  - Correct handling of PII masking and restoration
  - Explicit grounding in local policy sources
  - Tool usage safety and validation
  - That the `main` branch remains deployable
- Encourage at least one reviewer from security or compliance when the feature changes data handling.

## Release and merge policy
- `main` should always remain buildable and runnable.
- Final feature work is delivered via pull requests from a feature branch into `main`; for this repository, the branch `feat-rag-agent-system` is the intended feature branch used to deliver the completed agent.
- Merge only after passing tests and review approval.
- Use `main` for release tags and deployment.

## Quality practices
- Keep code modular and well-documented.
- Favor explicit logic over hidden side effects.
- Use `unittest` or `pytest` for regression coverage.
- Keep the architecture doc aligned with the actual code path.




