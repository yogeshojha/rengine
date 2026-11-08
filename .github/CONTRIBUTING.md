# Contributing to reNgine
[![first-timers](https://img.shields.io/badge/first--timers--only-friendly-blue.svg?style=flat-square)](https://www.firsttimersonly.com/)

Code, documentation, bug reports and feature proposals are accepted as issues and pull requests.

Developer chat is in the [Discord development channel](https://discord.gg/JuhHdHTtwd).

## Bug reporting

Before submitting a bug report, check the following:

1. Support requests go to the [Discord support channel](https://discord.gg/azv6fzhNCE), not the issue tracker.
2. Search existing issues before opening a new one.
3. Include the reNgine version, the steps that trigger the error and the full error message.
4. List the steps to reproduce it.

Report bugs in [GitHub Issues][1].

[1]: https://github.com/yogeshojha/rengine/issues/new


## Feature requests
Describe the problem the feature solves and the expected result.

## Pull requests

Open an issue before starting a large change such as a new feature or a refactor.

Development setup is in [dev-README.md](../dev-README.md). Run `make lint` and `make test` before opening a pull request.

### First time contributors

1. Fork this project.
2. `git clone https://github.com/<username>/rengine.git`
3. Add the upstream remote:
```
cd rengine
git remote add upstream https://github.com/yogeshojha/rengine.git
```
4. Pull the latest changes from upstream before starting:
```
git checkout master
git pull upstream master
```
5. Commit the change in logical steps.

## Code of Conduct

This project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). Participation means agreeing to its terms.
