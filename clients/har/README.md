# HAR importer

Sends a proxy's exported history to reNgine's connector ingest endpoint. Every proxy
exports HAR — ZAP, mitmproxy, Burp, and every browser's developer tools — so this is
the path for any proxy without a native client.

```
python3 rengine_har.py \
  --endpoint https://rengine.example.com/api/v1/connectors/ingest \
  --token rngconn_... \
  --client zap \
  history.har
```

Python 3 and nothing else. `--dry-run` prints what would be sent and sends nothing.

## What leaves your machine

The shape of each request only: the URL, the method, the status, the content type and
length, the page title, the **names** of any body parameters, and whether the request
carried a session. Headers, cookies and bodies stay where they are — the Burp client
sends no more than this either, and the contract is the same one.

An out-of-scope request is still sent. reNgine decides scope server-side and keeps an
unmatched request as unassigned rather than discarding it, so adding the target later
attaches everything already recorded.

## What it does on its own

- Drops anything that is not an `http`/`https` URL.
- Collapses repeats of the same method and URL, to keep the wire small. reNgine does
  the real shaping (`/api/users/1234` and `/api/users/9999` are one candidate).
- Sends in batches of 500.
- **Stops after a single 401.** The ingest endpoint sits behind a per-IP failure
  limiter, so retrying a rotated token locks you out. Rotate it in reNgine and run
  again.
