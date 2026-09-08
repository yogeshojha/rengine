# reNgine Connector for Burp Suite

Sends requests observed in Burp to a reNgine connector, where they are recorded as request shapes.

Works on Burp Suite Community and Professional. The extension uses no Professional-only API.

## Build

Needs a JDK 17 or later and nothing else. The Montoya API is downloaded on first build and is
`compileOnly`, so the jar carries no dependencies.

```
./build.sh
```

The path of the built jar is printed on the last line. A `build.gradle.kts` is included for anyone
who prefers Gradle; both produce the same artifact.

## Install

1. In reNgine, open **Connectors → New connector**, choose **Burp Suite**, and copy the token. It is
   shown once.
2. In Burp, go to **Extensions → Installed → Add**, extension type **Java**, and select the jar.
3. Open the **reNgine** tab, enter the ingest endpoint and the token, and press **Test connection**.
4. Tick **Send captured requests to reNgine**.

## reNgine on a VPS

Every request the extension makes is outbound, in both directions: observations are posted, and
queued work is collected rather than pushed. A machine behind NAT needs no inbound access and no
tunnel.

Three requirements:

- **The endpoint must be reachable from this machine.** The value shown when the connector is created
  is derived from the request that created it, so it is correct behind a configured reverse proxy.
  Behind one that terminates TLS without `--proxy-headers` on uvicorn it reads `http://`. The field
  is editable.
- **HTTPS.** The token is a bearer credential. Over plain HTTP to anything but localhost it is sent
  unencrypted, and the tab reports it.
- **Self-signed certificates are rejected by default.** *Accept a self-signed certificate* disables
  verification for this connection only.

## What it sends

One record per response, holding the URL, method, status code, content type, response length, page
title for HTML, whether the request carried a session, the originating Burp tool, and the names of
body parameters. **Parameter values, request bodies and response bodies are never sent.**

Only Proxy and Repeater traffic is eligible. Scanner and Intruder traffic is never captured, so a
fuzzing run does not enter the inventory.

## Working on

The reNgine tab has a **Working on** picker, filled from reNgine over the same connection. Choose the
target being tested and every captured request is tagged to it, whatever the hostname. Left on
*Match by hostname*, each request is matched by its host; anything unmatched is still recorded and
appears in reNgine as unassigned.

**Apply scope to Burp** sets Burp's own target scope from what reNgine knows: every hostname it has
discovered for that target, plus the out-of-scope rules of a bug bounty program when the target came
from one.

The tab also reports what reNgine already knows about the host most recently captured — how many
endpoints scans have found there, and how many of them have been reached.

## Sending back

reNgine can hand work to the proxy. Select shapes on the Connectors page and press **Send to
Repeater**; the extension collects them within a few seconds and opens each in a Repeater tab named
after its path.

The proxy asks, reNgine never pushes. An action is delivered once and never replayed, and one left
uncollected for an hour is dropped rather than opening tabs from yesterday's session.

## reNgine speaks back

The tab carries a **From reNgine** list: the last few things worth knowing, collected on the same
poll as queued work. An out-of-scope host is also raised in Burp's own event log, because that one
must not be missed while concentrating on something else.

## Reporting a finding

Right-click any request in Proxy or Repeater and choose **Report to reNgine**. Give it a title and a
severity; the request and response travel with it as evidence.

The finding is recorded against the tested target under a run named *Manual testing · <connector>*,
with `scanner = manual`, so it behaves like any other finding: triage, `is:new` across later scans,
reports and compliance mapping all apply. Reporting the same thing twice is one finding.

## What it does not do

- It does not block or delay the request path. Records are queued and posted on a background thread;
  when the queue is full, records are dropped and counted rather than made to wait.
- It does not re-send a URL it has already reported within the last minute.
- It does not shape or deduplicate structurally. reNgine folds `/api/users/1` and `/api/users/2` into
  one shape server-side, so that rule has one definition.

## Settings

| Setting | Effect |
|---|---|
| Ingest endpoint | The reNgine URL to post to. Shown when the connector is created. |
| Connector token | Authenticates the connector. Stored in Burp's preference store. |
| Send captured requests | The master switch. Nothing is sent while it is off. |
| Proxy traffic | Capture requests made through the proxy. |
| Repeater requests | Capture requests sent by hand. |
| Only hosts in Burp's target scope | Pre-filter using Burp's own scope. reNgine applies its own scope regardless. |
| Read page titles from HTML responses | Extract `<title>` from HTML bodies up to 256 KB. |

## Layout

| Path | Purpose |
|---|---|
| `ReNgineConnector.java` | Extension entry point and lifecycle |
| `Capture.java` | The HTTP handler; converts a response into an observation |
| `Sink.java` | Bounded queue, background flush, batch POST. No Burp dependency |
| `Actions.java` | Collects queued work and notices. No Burp dependency |
| `Notices.java` | The last few things reNgine said, bounded |
| `Report.java` / `ReportMenu.java` | Reporting a finding, and the right-click that starts it |
| `Settings.java` | Configuration, persisted in Burp preferences |
| `ConnectorTab.java` | The reNgine tab |
| `Json.java`, `Observation.java` | Minimal JSON writer and the wire record |

`Sink` deliberately knows nothing about Burp so it can be exercised without the suite:

```
javac --release 17 -cp build/classes -d build/test-classes src/test/java/io/rengine/connector/*.java
java -cp build/classes:build/test-classes io.rengine.connector.SinkHarness <endpoint> <token> <host>
java -cp build/classes:build/test-classes io.rengine.connector.ActionsHarness
```

The connector token is held in Burp's own preference store, in plain text, as Burp extensions
normally do. Treat a Burp project file as you would the token itself.
