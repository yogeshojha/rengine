# Contributing to reNgine

[![first-timers](https://img.shields.io/badge/first--timers--only-friendly-blue.svg?style=flat-square)](https://www.firsttimersonly.com/)

As an open-source project, reNgine welcomes any contributions. Your contributions could be as simple as fixing the indentations or fixing UI to as complex as bringing new modules and features.
Your contributions are highly appreciated and we welcome any kind of contributions as long as you adhere to our guidelines and your PR aligns the idea behind creating the reNgine.

If you are new to open source community, reNgine is beginner-friendly. Please create pull requests for any new features, bug fixes, improvements on documentation, or anything!

Join our developer chat on [reNgine Slack channel](https://join.slack.com/t/reconengine/shared_invite/zt-figje4iu-~tgPstZXzqiBrDzl4Y1j5Q) if you would like to contribute to reNgine.

- [Types of Contributions](#Types-of-Contributions)
- [Contributor Setup](#Setting-Up-the-Code-for-Local-Development)
- [Contributor Guidelines](#Contributor-Guidelines)
- [Contributor Testing](#Testing-with-tox)
- [Core Committer Guide](#Core-Committer-Guide)

## Types of Contributions

You can contribute in many ways:

## Bug reporting

We appreciate your effort to improve reNgine by submitting a bug report. But, Before doing so, please check the following things:

1. Please **do not** use the issue tracker for personal support requests, instead use [reNgine Slack channel](https://join.slack.com/t/reconengine/shared_invite/zt-figje4iu-~tgPstZXzqiBrDzl4Y1j5Q) for any personal support request.
2. Check whether the bug **hasn't been already reported**. Duplicate reports take us time, that we could be used to fix other bugs or make improvements.
3. If you get an error while using reNgine, please **describe what happened** and add a verbose error message. Reports like "I got an error when I started scanning some random website." are not worth anybody's time. Please be as descriptive as you can.
4. Provide easy steps to reproduce. This will help us solve your issues easily and quickly.
   Your contributions are again highly appreciated!

Please report [bugs here on GitHub Issues section][1].

[1]: https://github.com/yogeshojha/rengine/issues/new

## Feature requests

We welcome feature requests. But please take a moment to find out whether your idea fits with the original idea behind reEngine. It's up to you to make a strong case to convince the project's developers of the merits of this feature. Please provide as much detail and context as possible.

## Pull requests

Pull requests with a bug fix, improvements, new features are welcome and very much appreciated.

**Please ask** first before embarking on any significant pull request (e.g. implementing features, refactoring code, porting to a different language), otherwise you risk spending a lot of time working on something that the project's developers might not want to merge into the project.

## Submit Feedback

The best way to send feedback is to file an issue at [https://github.com/yogeshojha/rengine/issues](https://github.com/yogeshojha/rengine/issues).

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome :)

### First Time Contributors

If reNgine happens to be your first open-source project to contribute to, please follow the guidelines.

1. Fork this project.
2. `git clone https://github.com/yourusername/rengine.git`
3. Configure the remote as below

```
cd rengine
# Assign upstream
git remote add upstream https://github.com/yogeshojha/rengine.git
```

4. If cloning was done a while ago, please get the latest changes from upstream

```
git checkout master
git pull upstream master
```

5. Commit your changes in the logical chunks

## Contributor Guidelines

### Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated and add the feature to the list in README.md.
3. The pull request must pass all CI/CD jobs before being ready for review.
4. If one CI/CD job is failing for unrelated reasons you may want to create another PR to fix that first.

### Coding Standards

- PEP8
- Write code in Python 3.

## Core Committer Guide

### Vision and Scope

Core committers, use this section to:

- Guide your instinct and decisions as a core committer
- Limit the codebase from growing infinitely

#### Inclusive

- Cross-platform and cross-version support are more important than features/functionality
- Fixing Windows bugs even if it's a pain, to allow for use by more beginner coders

#### Stable

- Aim for 100% test coverage and covering corner cases
- No pull requests will be accepted that drop test coverage on any platform, including Windows
- Conservative decisions patterned after CPython's conservative decisions with stability in mind

### Process: Pull Requests

If a pull request is untriaged:

- Look at the roadmap
- Set it for the milestone where it makes the most sense
- Add it to the roadmap

How to prioritize pull requests, from most to least important:

- Minor edits to docs.
- Bug fixes.
- Major edits to docs.
- Features.

Ensure that each pull request meets all requirements.

### Process: Issues

If an issue is a bug that needs an urgent fix, mark it for the next patch release.  
Then either fix it or mark as please-help.

For other issues: encourage friendly discussion, moderate debate, offer your thoughts.

New features require a +1 from 2 other core committers (besides yourself).

### Process: Pull Request merging and maintenance

When you're processing the first change after a release, create boilerplate following the existing pattern:

```md
## x.y.z (Development)

The goals of this release are TODO: release summary of features

Features:

- Feature description, thanks to [@contributor](https://github.com/contributor) (#PR).

Bug Fixes:

- Bug fix description, thanks to [@contributor](https://github.com/contributor) (#PR).

Other changes:

- Description of the change, thanks to [@contributor](https://github.com/contributor) (#PR).
```

### Process: Your own code changes

All code changes, regardless of who does them, need to be reviewed and merged by someone else.  
This rule applies to all the core committers.

Exceptions:

- Minor corrections and fixes to pull requests submitted by others.
- While making a formal release, the release manager can make necessary, appropriate changes.
- Small documentation changes that reinforce existing subject matter. Most commonly being, but not limited to spelling and grammar corrections.

### Responsibilities

- Ensure cross-platform compatibility for every change that's accepted. Windows, Mac, Debian & Ubuntu Linux.
- Create issues for any major changes and enhancements that you wish to make. Discuss things transparently and get community feedback.
- Keep feature versions as small as possible, preferably one new feature per version.
- Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. Look at [Code of Conduct](CODE_OF_CONDUCT.md).

### Becoming a Core Committer

Contributors may be given core commit privileges. Preference will be given to those with:

1. Past contributions to rengine and other open-source projects. Contributions to rengine include both code (both accepted and pending) and friendly participation in the issue tracker. Quantity and quality are considered.
2. A coding style that the other core committers find simple, minimal, and clean.
3. Access to resources for cross-platform development and testing.
4. Time to devote to the project regularly.

## Code of Conduct

Please note that this project is released with a [Contributor Code of
Conduct](/CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

## Thank you!

Thank you for contributing!
