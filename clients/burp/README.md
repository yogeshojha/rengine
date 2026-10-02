# reNgine Connector for Burp Suite

Sends requests observed in Burp to a reNgine connector. They are recorded as endpoints of the
target under test. The target's scope is pushed into Burp, and scan-recorded endpoints that were
not opened are listed.

Works on Burp Suite Community and Professional. The extension uses no Professional-only API.

## Install

1. In reNgine, open **Connectors**, press **Connect Burp Suite**. The dialog shows the endpoint,
   the token and a Download button for the jar. The token is shown once. **Setup** on the Burp
   Suite card reopens the dialog. A project holds one Burp Suite connection.
2. In Burp, go to **Extensions → Installed → Add**, extension type **Java**, and select the jar.
3. Open the **reNgine** tab, paste the endpoint and the token, press **Save and test**. The header
   of the tab and the connector's row in reNgine both read **Connected**.
4. Under **Working on**, pick the target and press **Apply scope to Burp**. Tick **Send captured
   requests to reNgine**.

## Build

Needs a JDK 17 or later. The Montoya API jar is downloaded to `lib/` on first build and is not
packaged. The jar carries no dependencies.

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
  verification for this connection only, the name on the certificate included.
- **HTTP/2 over HTTPS, HTTP/1.1 otherwise.** An HTTPS endpoint is negotiated to HTTP/2 and falls
  back to HTTP/1.1 when the server does not offer it. A plain HTTP endpoint uses HTTP/1.1.
- **The endpoint is the address reNgine is installed under.** An install by IP address answers on
  that address only. A bare origin such as `https://rengine.example.com` is completed with the
  ingest path on save.

## What it sends

One record per response: the URL, method, status code, content type, response length, page title
for HTML, whether the request carried a session, the originating Burp tool, and the names of body
parameters. **Request bodies and response bodies are not sent.**

With *Send request headers* on, each record also carries the request line and headers. Cookie,
Authorization and token header values are masked before they leave Burp. reNgine keeps the sample
only when the connector's *Request samples* setting is on.

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

Findings, web assets, endpoints and browsed requests carry a **Send to Repeater** button: on the
finding sheet, the web asset sheet, the endpoint rows and branches, and every selection bar. The
arrow beside it picks another tool, and the button keeps the last one chosen. With Burp offline
the request is queued and the button reads **Queued for Burp Suite**.

| Tool | What arrives |
|---|---|
| Repeater | One tab per request, named after the check or the path. |
| Intruder | One attack per request. |
| Organizer | Request and response, with the finding as a note and a highlight by severity. |
| Site map | Request and response under the host in Target. |

The request is the one reNgine stored: the exact request nuclei sent for a finding, the probe's
request for a web asset, the request the proxy recorded for a browsed shape. An endpoint nothing
stored a request for gets one built from its method, URL and parameters; a POST, PUT or PATCH
carries a body template in the declared type, JSON, multipart, XML or form. A finding with no
HTTP exchange, a DNS or TLS check, is skipped and counted in the reply. Responses arrive decoded,
as UTF-8, with the length of what was stored; a binary response arrives as its headers.

Header values a scan masked arrive masked. The connector setting *Restore masked headers* fills
them from the run that sent the request, at collection time. A request collected with the
connector token then carries those values.

The extension polls for queued requests. Each is delivered once. One left uncollected for an
hour is dropped.

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
- It does not drop a batch on an outage. A batch reNgine did not answer, or answered with 429 or
  a server error, is held and sent again, up to eight attempts with a wait of 2 to 30 seconds.
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
| Send request headers | Add the request line and headers to each record, credential values masked. |
| Accept a self-signed certificate | Disable certificate verification for this connection. |

## Layout

| Path | Purpose |
|---|---|
| `ReNgineConnector.java` | Extension entry point and lifecycle |
| `Capture.java` | The HTTP handler; converts a response into an observation |
| `Sink.java` | Bounded queue, background flush, batch POST. No Burp dependency |
| `Actions.java` | Collects queued requests and notices. No Burp dependency |
| `Handoff.java` | Opens a queued request in Repeater, Intruder, Organizer or the site map |
| `Notices.java` | The last notices from reNgine, bounded |
| `Facts.java`, `Targets.java` | Scope, host facts and the target picker |
| `Report.java` / `ReportMenu.java` | Reporting a finding, and the right-click that starts it |
| `Settings.java` | Configuration, persisted in Burp preferences |
| `Tls.java` | HTTP clients and the self-signed certificate switch |
| `ConnectorTab.java` | The reNgine tab |
| `Json.java`, `Observation.java` | Minimal JSON writer and the wire record |

The connector token is held in Burp's preference store in plain text. A Burp preference export
carries the token.

## Tests

`./test.sh` compiles the extension with `-Werror` and runs the offline checks. `SinkHarness`
posts to a running reNgine: `java -cp 'lib/*:build/classes:build/test-classes'
io.rengine.connector.SinkHarness <ingest url> <token> [host]`.
