# OwnMachine contribution workflow

Use the configured Git `origin` remote; never embed a developer’s private server address in project files.

Use Gitflow through pull requests for every change:

- `main` contains released code; `develop` is the integration branch.
- Branch `feature/<description>` from `develop`; submit a PR into `develop`.
- Branch `release/<version>` from `develop`; submit a release PR into `main`,
  then a synchronization PR back into `develop` and tag the released commit.
- Branch `hotfix/<description>` from `main`; submit PRs into `main` and `develop`.
- Never push directly to `main` or `develop`, force-push protected branches,
  or bypass their PR requirements. The initial empty repository bootstrap is
  the sole exception, already completed before protection was enabled.
- Use merge commits for Gitflow integration so branch history is retained.
- Keep implementation and documentation changes in reviewable commits. Include
  the problem, behavior change, test evidence, and remaining limitations in PRs.
- Run `python -m unittest discover -s tests -v` and Hermes plugin validation
  before requesting merge. Do not claim hardware tests that have not run.
- Do not merge a PR unless the user explicitly requests it.
- Never commit credentials, runtime state, VM disks, or private desktop captures.

Only `plugin/` is the installable Hermes package. Keep operator scripts, tests
and host relay outside that package; catalog metadata must use `subdir: plugin`.
Never evade validation by suppressing findings or renaming privileged operations.
Install the plugin under the active Hermes home’s `plugins/ownmachine` directory.
Deployments must identify their source branch/commit; do not copy `.git` into the
installed plugin. Keep hostnames, IP addresses, account names, SSH credentials,
and deployment paths in operator-owned configuration outside the repository.
All documentation and scripts must work for arbitrary user accounts. Use reserved
example domains or explicit placeholders when an example needs a host identity.
