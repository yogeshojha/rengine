# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

- [Types of Contributions](#Types-of-Contributions)
- [Contributor Setup](#Setting-Up-the-Code-for-Local-Development)
- [Contributor Guidelines](#Contributor-Guidelines)
- [Contributor Testing](#Testing-with-tox)
- [Core Committer Guide](#Core-Committer-Guide)

## Types of Contributions

You can contribute in many ways:

### Report Bugs

Report bugs at [https://github.com/yogeshojha/rengine/issues](https://github.com/yogeshojha/rengine/issues).

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- If you can, provide detailed steps to reproduce the bug.
- If you don't have steps to reproduce the bug, just note your observations in as much detail as you can. Questions to start a discussion about the issue are welcome.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features . Anything tagged with "enhancement" and "bug" is open to whoever wants to implement it.

Please do not combine multiple feature enhancements into a single pull request.

Note: this project is very conservative, so new features that aren't tagged with "please-help" might not get into core. We're trying to keep the code base small, extensible, and streamlined. Whenever possible, it's best to try and implement feature ideas as separate projects outside of the core codebase.

### Submit Feedback

The best way to send feedback is to file an issue at [https://github.com/yogeshojha/rengine/issues](https://github.com/yogeshojha/rengine/issues).

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome :)

## Setting Up the Code for Local Development

Here's how to set up `Rengine` for local development.

1. Fork the `Rengine` repo on GitHub.
2. Clone your fork locally:

```bash
git clone git@github.com:your_name_here/rengine.git
```

3. Assuming you have docker installed, this is how you set up your fork for local development:

```bash
cd engine
docker-compose up --build -d

# Build process may take some time 3. Run the migration
docker exec -it rengine_web_1 python manage.py migrate

docker-compose up -d

```

4. Create a branch for local development :

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

5. Commit your changes and push your branch to GitHub:

```bash
git add .
git commit -m "Your detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

8. Submit a pull request through the GitHub website.

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

Ensure that each pull request meets all requirements in [checklist](https://gist.github.com/audreyr/4feef90445b9680475f2).

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
