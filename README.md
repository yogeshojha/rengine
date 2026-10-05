<p align="center">
  <a href="https://rengine.wiki"><img src=".github/screenshots/banner.gif" alt="reNgine" /></a>
</p>

<h3 align="center">reNgine: Open Source Attack Surface Management</h3>

<p align="center">
  <a href="https://github.com/yogeshojha/rengine/releases"><img src="https://img.shields.io/badge/version-v3.0.0-informational?&logo=none" alt="Latest version" /></a>&nbsp;
  <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-red.svg?&logo=none" alt="GPLv3" /></a>&nbsp;
  <a href="https://github.com/yogeshojha/rengine/actions/workflows/build.yml"><img src="https://github.com/yogeshojha/rengine/actions/workflows/build.yml/badge.svg" alt="Build" /></a>&nbsp;
  <a href="https://github.com/yogeshojha/rengine/actions/workflows/codeql-analysis.yml"><img src="https://github.com/yogeshojha/rengine/actions/workflows/codeql-analysis.yml/badge.svg" alt="CodeQL" /></a>&nbsp;
  <a href="https://discord.gg/H6WzebwX3H"><img src="https://img.shields.io/discord/880363103689277461" alt="Discord" /></a>
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg"><img src="https://img.shields.io/badge/BlackHat--Arsenal--Asia-2023-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg"><img src="https://img.shields.io/badge/BlackHat--Arsenal--USA-2022-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg"><img src="https://img.shields.io/badge/Open--Source--Summit-2022-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://cyberweek.ae/2021/hitb-armory/"><img src="https://img.shields.io/badge/HITB--Armory-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=7uvP6MaQOX0"><img src="https://img.shields.io/badge/BlackHat--Arsenal--USA-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://drive.google.com/file/d/1Bh8lbf-Dztt5ViHJVACyrXMiglyICPQ2/view?usp=sharing"><img src="https://img.shields.io/badge/Defcon--Demolabs--29-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=A1oNOIc0h5A"><img src="https://img.shields.io/badge/BlackHat--Arsenal--Europe-2020-blue.svg?&logo=none" alt="" /></a>
</p>

<h4>reNgine 3.0 Sirius is released</h4>
<p>
  reNgine 3.0 Sirius is a complete rewrite of reNgine as an attack surface management platform. It brings a seven-dimension attack surface model, a query language across all results, correlation of assets across targets, exploit intelligence from EPSS and KEV, software CVE inference, secret mining, run comparison, program watches for bug bounty scopes, an MCP server, remote control over Telegram and a Burp Suite connector.
  <b>Read <a href="https://rengine.wiki/whats-new/3_0_0/">What's new in reNgine 3.0</a>.</b>
</p>

<h4>What is reNgine?</h4>
<p>
  reNgine is an open source attack surface management platform for security teams, penetration testers and bug bounty hunters. It maps the external attack surface of an organisation, finds subdomains, IP addresses, open ports, endpoints and running software, scans them for vulnerabilities, and keeps the results in one place. Scans are built from configurable engines, results are searched with a query language, and every scan can be scheduled, compared with the previous one and reported on.
</p>
<p>
  reNgine runs on your own server with Docker Compose and works with the open source tools the community already trusts, including subfinder, httpx, naabu, katana, ffuf, nuclei and dalfox.
</p>

## Documentation

Detailed documentation is available at [rengine.wiki](https://rengine.wiki).

## Table of Contents

* [About reNgine](#about-rengine)
* [Features](#features)
* [Quick Installation](#quick-installation)
* [Updating](#updating)
* [Upgrading from reNgine 2.x](#upgrading-from-rengine-2x)
* [What's new in reNgine](https://github.com/yogeshojha/rengine/releases)
* [Contributing](#contributing)
* [reNgine Support](#rengine-support)
* [Support and Sponsoring](#support-and-sponsoring)
* [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)
* [License](#license)

## About reNgine

**Attack surface, not a subdomain list.** Every scan produces seven kinds of result: web assets, endpoints, services, IP addresses, vulnerabilities, software CVEs and secrets. Each kind has its own page across all targets in a project and its own tab on every scan. A target can be a domain, an IP address, an IP range, an ASN or a URL.

**Scan engines.** A scan engine is a saved set of stages: subdomain discovery, host discovery, port scanning, HTTP probing, screenshots, URL discovery, content discovery, vulnerability scanning, DAST fuzzing, secret mining and more. Each stage has its own settings, every engine can run at passive, normal or aggressive intensity, and a scan context supplies authentication headers, scope exclusions, proxies and rate limits for the target. Any stage can be overridden for a single run, and a focused rescan runs selected stages against selected assets.

**Query language.** All results are searchable with the same query syntax. `is:live tech:nginx` finds live nginx web assets, `severity:critical is:new` finds critical findings not seen in any earlier scan of the target, `port:22` finds SSH services and `cve:CVE-2024-3400` finds every asset affected by one CVE. Queries drive filters, saved rules, dashboard counts, exports and notifications.

**Correlation.** Hosts that share an IP address, certificate, page title, favicon, body hash, JARM fingerprint, technology or CDN are grouped and drawn as a graph. Links are drawn across targets in a project, and targets are related to each other by certificate, registrant, network and nameserver. Provider infrastructure such as CDN edges and shared platform hostnames is recognised and not drawn as a relation.

**Prioritisation.** Findings carry CVSS, EPSS and CISA KEV data, refreshed nightly from the feeds without a rescan. Software CVEs are inferred from fingerprinted versions against a local NVD corpus and shown as their own dimension. Every finding sits on one evidence ladder, from inferred to proven, and triage decisions carry across scans.

**Continuous monitoring.** Scans run once, on an interval, daily at a fixed time or on a cron expression. What's new lists everything found since the last visit, grouped by run, and Compare runs shows the difference between any two scans of a target, including what changed in the configuration between them. Notifications go to Slack, Discord, Telegram, Microsoft Teams, email and webhooks.

**Bug bounty mode.** Bounty Hub syncs programs and scopes from HackerOne and Intigriti and imports the public program feed. A program watch turns a program's scope into targets, a scan context and a schedule, then follows certificate transparency logs and probes each new in-scope host as its certificate appears.

**Integrations.** An MCP server exposes reNgine's data and scan controls to AI agents with scoped service tokens. Remote control pairs a Telegram chat with the instance for scans, findings and progress from a phone. The Burp Suite connector feeds proxy traffic into the endpoint inventory and sends endpoints back to Burp. AI providers can be connected for report narration and exposure review.

**Reports.** PDF reports are assembled from sections such as executive summary, risk summary, findings, web assets, services, hosting, domain posture and remediation plan, styled with themes. Any result set exports as CSV, JSON or text.

## Features

* Reconnaissance
  * Subdomain discovery from passive sources, certificate transparency, wordlists and permutations
  * IP address, ASN and country enrichment without an API key
  * Netblock sweeps and reverse DNS for ASN and IP range targets
  * Port scanning with service fingerprinting and banner grabbing
  * HTTP probing with technology, web server, TLS, CDN, WAF and favicon detection
  * URL discovery from crawling, archives and sitemaps
  * Content discovery with calibrated fuzzing
  * Virtual host discovery, zone transfer checks and subdomain takeover detection
  * Screenshot gallery with clustering of pages that look alike
* Vulnerability assessment
  * Vulnerability scanning with nuclei over a planned input set
  * DAST fuzzing with nuclei and dalfox
  * Software CVE inference against a local NVD corpus
  * Secret mining across stored responses
  * Web hygiene checks on headers, cookies, CSP and CORS
  * Domain posture checks on SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA
  * EPSS and CISA KEV exploit intelligence, refreshed nightly
  * Evidence ladder and triage carried across scans
* Attack surface management
  * Seven result dimensions across targets and per scan
  * Query language with autocomplete and saved rules
  * Correlation graph and cross-target links
  * Exposures from rules and correlation signals
  * What's new since the last visit
  * Compare any two runs of a target
  * Recon notes anchored to assets
  * Bulk triage, selection and export
* Scanning
  * Scan engines built from stages, with a built-in engine per project
  * Passive, normal and aggressive intensity
  * Scan contexts for authentication, scope, proxies and rate limits
  * Single-run overrides and focused rescans
  * Pause, resume and cancel
  * One-off, interval, daily and cron schedules
  * Projects for separating engagements
* Bug bounty
  * Bounty Hub with HackerOne and Intigriti sync and the public program feed
  * Program watches with certificate transparency monitoring
* Integrations
  * MCP server for AI agents
  * Remote control over Telegram
  * Burp Suite connector
  * OpenAI, Anthropic, Google and OpenAI-compatible AI providers
  * Notifications on Slack, Discord, Telegram, Microsoft Teams, email and webhooks
* Reporting
  * PDF reports from configurable sections and themes
  * CSV, JSON and text exports
* Toolbox for one-off lookups: WHOIS, DNS, subdomains, HTTP probe, IP intelligence and CVE
* Arsenal for nuclei templates, wordlists and threat intelligence feeds
* Two-factor authentication and encrypted API keys

## Quick Installation

reNgine installs on a Linux host, local or VPS, with one script. It checks for Docker and Docker Compose v2, sizes the database for the machine, generates the secrets and starts the stack behind a Caddy reverse proxy that terminates HTTPS.

```bash
curl -fsSL https://raw.githubusercontent.com/yogeshojha/rengine/master/install.sh -o install.sh
sudo bash install.sh
```

The guided setup asks where the instance is reached: a public domain with a Let's Encrypt certificate, a server address with a self-signed certificate, or this machine only. It then asks for the UI port, whether the API is also published over plain HTTP on 127.0.0.1, and the administrator credentials. Everything else is generated. The UI, agents and connectors all reach the API at `/api` on the same origin, so no other port needs to be open.

For an unattended install, pass the answers as flags:

```bash
sudo bash install.sh --domain asm.example.com
sudo bash install.sh --local --ui-port 8080
```

The administrator password comes from the prompt, from stdin with `--admin-password-stdin` or from `RENGINE_ADMIN_PASSWORD`, and is generated when none is given. `install.sh --help` lists every option. 4 GB of memory and 10 GB of disk are the minimum. 8 GB of memory and 25 GB of disk are recommended for regular scanning.

Images are published for amd64 and arm64 on Docker Hub and on the GitHub Container Registry. `--image ghcr.io/yogeshojha/rengine` installs from the second, and `--image` also takes the prefix of a private mirror.

After the install, the `rengine` command manages the instance:

```bash
sudo rengine status      # services and API health
sudo rengine logs api    # follow one service
sudo rengine backup      # archive the database, scan media and settings
sudo rengine update      # move to the latest release
```

A backup holds the instance key. Run from a terminal, `rengine backup` asks for a passphrase and encrypts the archive with it.

To regain access to an account, `sudo rengine reset-password <username>` asks for a new password and signs the account out everywhere. `--remove-2fa` also removes two-factor authentication. A password piped to stdin skips the prompt.

### From source

A checkout installs the same way with images built locally instead of pulled:

```bash
git clone https://github.com/yogeshojha/rengine && cd rengine
sudo bash install.sh --build
```

For development with hot reload, copy `.env.example` to `.env`, set a secret key and the credentials, then `docker compose up -d --build` and `make migrate`. The development UI serves at `http://127.0.0.1:5173`.

## Updating

```bash
sudo rengine update
```

The update pulls the new images, saves a database snapshot to `backups/`, stops the services, applies the migrations and starts the new release. Running scans resume afterwards and repeat the stages that were in flight. `rengine update --no-backup` skips the snapshot.

To return to the earlier release, run `rengine update v<earlier> --no-backup`. If the database was already migrated, follow it with `rengine restore backups/<snapshot>`.

A source install updates with `git pull`, then `install.sh --build`.

## Upgrading from reNgine 2.x

reNgine 3.0 uses a new data model and does not import a 2.x database. Install 3.0 as a new instance and add targets again.

## Contributing

Contributions of all sizes are welcome: code, documentation, bug reports, feature proposals and interface work.

1. Read the [Contributing Guide](.github/CONTRIBUTING.md)
2. Pick an [open issue](https://github.com/yogeshojha/rengine/issues) or propose a new one
3. Fork the repository and create a branch
4. Make the change, run `make lint` and `make test`, and open a pull request

Development setup and commands are in [dev-README.md](dev-README.md). First-time open source contributors are welcome.

## reNgine Support

Read the [documentation](https://rengine.wiki) before asking for help. Most questions are answered there.

* Do not use GitHub issues for support requests.
* Join the [community-maintained Discord](https://discord.gg/azv6fzhNCE). There is no guaranteed response time.
* Open a GitHub issue for confirmed bugs and feature requests.

## Support and Sponsoring

reNgine is a passion project developed alongside a day job. Support it by:

* Adding a [GitHub Star](https://github.com/yogeshojha/rengine)
* Writing or posting about reNgine
* Nominating the author for [GitHub Stars](https://stars.github.com/nominate/)
* Sponsoring through the links in [FUNDING.yml](.github/FUNDING.yml)

## Reporting Security Vulnerabilities

1. Do not disclose the vulnerability in a public issue or forum.
2. Open the [Security tab](https://github.com/yogeshojha/rengine/security) and choose "Report a vulnerability".
3. Include steps to reproduce, the impact and any suggested fix.

Reports are usually answered within 72 hours. Responsible disclosure is credited after the fix is released, unless the reporter prefers to stay anonymous. See [SECURITY.md](.github/SECURITY.md).

## License

Distributed under the GNU GPL v3 License. See [LICENSE](LICENSE) for more information.
