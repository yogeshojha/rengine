# reNgine Connector for Burp Suite

Sends requests observed in Burp to a reNgine connector. They are recorded as endpoints of the
target under test. The target's scope is pushed into Burp, and scan-recorded endpoints that were
not opened are listed.

Works on Burp Suite Community and Professional. The extension uses no Professional-only API.

## Install

1. In reNgine, open **Connectors**, press **New connector**. The next dialog shows the endpoint,
   the token and a Download button for the jar. The token is shown once.
2. In Burp, go to **Extensions → Installed → Add**, extension type **Java**, and select the jar.
3. Open the **reNgine** tab, paste the endpoint and the token, press **Test connection**.
4. Under **Working on**, pick the target and press **Apply scope to Burp**. Tick **Send captured
   requests to reNgine**.

## Build

Needs a JDK 17 or later. The Montoya API is downloaded on first build as a `compileOnly`
dependency. The jar carries no dependencies.

```
./build.sh
```

The jar lands in `build/` and is copied to `binaries/` at the repository root, which the api
serves.

## reNgine on a VPS

Every request the extension makes is outbound. Observations are posted and queued work is
polled. A machine behind NAT needs no inbound access and no tunnel.

- **The endpoint must be reachable from this machine.** The value shown when the connector is
  created is the address of the reNgine page in the browser. The field is editable.
- **HTTPS.** The token is a bearer credential. Over plain HTTP to anything but localhost it is sent
  unencrypted, and the tab reports it.
- **Self-signed certificates are rejected by default.** *Accept a self-signed certificate* disables
  verification for this connection only.

## What it sends

One record per response: the URL, method, status code, content type, response length, page title
for HTML, whether the request carried a session, the originating Burp tool, and the names of body
parameters. **Parameter values, request bodies and response bodies are not sent.**

Only Proxy and Repeater traffic is eligible. Scanner and Intruder traffic is not captured.

## Working on

The picker is filled from reNgine. Choose the target being tested and every captured request is
tagged to it, whatever the hostname. Left on *Match by hostname*, each request is matched by its
host. Anything unmatched is recorded as unassigned and attaches when the target is added.

**Apply scope to Burp** sets Burp's target scope from what reNgine knows: every hostname discovered
for that target, plus the out-of-scope rules of a bug bounty program when the target came from one.

The line under the picker reports the host most recently captured: how many endpoints scans
recorded there, how many of those were opened, and how many were not.

## Sending back

Select endpoints on the Endpoints page or shapes on the Connectors page and press **Send to Burp
Suite**. The extension collects them within a few seconds and opens each in a Repeater tab named
after its path. The request is bare: no session, no headers.

The extension polls for actions. An action is delivered once. One left uncollected for an hour is
dropped.

## From reNgine

The tab lists the last notices: sensitive paths, administrative interfaces, server errors, hosts a
program lists as out of scope. **Open in reNgine** opens the selected host on the Endpoints page.
An out-of-scope host is also raised in Burp's event log.

## Reporting a finding

Right-click any request in Proxy or Repeater and choose **Report to reNgine**. Enter a title, a
severity and notes. The request and response are stored as evidence with Cookie, Authorization
and token headers masked. A dialog reports the outcome.

The finding is recorded against the tested target under a run named *Manual testing · <connector>*,
with `scanner = manual`. Reporting the same thing twice is one finding.

## What it does not do

- It does not block the request path. Records are queued and posted on a background thread. When
  the queue is full, records are dropped and counted.
- It does not re-send a URL reported within the last minute.
- It does not shape or deduplicate. reNgine folds `/api/users/1` and `/api/users/2` into one shape
  server-side.

## Settings

| Setting | Effect |
|---|---|
| Endpoint | The reNgine URL to post to. |
| Token | Authenticates the connector. Stored in Burp's preference store. |
| Send captured requests to reNgine | The master switch. |
| Proxy traffic | Capture requests made through the proxy. |
| Repeater requests | Capture requests sent by hand. |
| Only hosts in Burp's target scope | Pre-filter using Burp's own scope. reNgine applies its own regardless. |
| Read page titles from HTML responses | Extract `<title>` from HTML bodies up to 256 KB. |
| Accept a self-signed certificate | Disable certificate verification for this connection. |

## Layout

| Path | Purpose |
|---|---|
| `ReNgineConnector.java` | Extension entry point and lifecycle |
| `Capture.java` | The HTTP handler; converts a response into an observation |
| `Sink.java` | Bounded queue, background flush, batch POST. No Burp dependency |
| `Actions.java` | Collects queued work and notices. No Burp dependency |
| `Notices.java` | The last notices from reNgine, bounded |
| `Facts.java`, `Targets.java` | Scope, host facts and the target picker |
| `Report.java` / `ReportMenu.java` | Reporting a finding, and the right-click that starts it |
| `Settings.java` | Configuration, persisted in Burp preferences |
| `ConnectorTab.java` | The reNgine tab |
| `Json.java`, `Observation.java` | Minimal JSON writer and the wire record |

The connector token is held in Burp's preference store in plain text. A Burp preference export
carries the token.
