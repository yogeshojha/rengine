package io.rengine.connector;

import java.net.ConnectException;
import java.net.NoRouteToHostException;
import java.net.URI;
import java.net.UnknownHostException;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.channels.UnresolvedAddressException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import javax.net.ssl.SSLException;
import javax.net.ssl.SSLHandshakeException;

/** Buffers observations off the proxy thread and posts them in batches. */
final class Sink {
    static final int QUEUE_CAPACITY = 5000;
    static final int MAX_BATCH = 200;
    static final long FLUSH_MILLIS = 2000;
    static final int DEDUPE_CAPACITY = 20000;
    static final long RESEND_AFTER_MILLIS = 60_000;
    static final int UNAUTHORIZED = 401;
    static final int TOO_MANY_REQUESTS = 429;
    static final String NOT_RENGINE =
            "The address answered, but not as a reNgine connector. Check the host and the path.";
    static final int MAX_ATTEMPTS = 8;
    static final long RETRY_MIN_MILLIS = 2000;
    static final long RETRY_MAX_MILLIS = 30_000;

    interface Log {
        void line(String message);
    }

    /** Where to post. */
    interface Config {
        String endpoint();

        String token();

        boolean isConfigured();

        boolean allowSelfSigned();

        /** Incremented on every save. */
        long generation();

        /** The target chosen while testing, or null to match each request by hostname. */
        String targetId();

        /** The program chosen while testing; each host is matched within it. */
        String programId();
    }

    private final BlockingQueue<Observation> queue = new ArrayBlockingQueue<>(QUEUE_CAPACITY);
    private final Map<String, Long> recent = new LinkedHashMap<>(1024, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Long> eldest) {
            return size() > DEDUPE_CAPACITY;
        }
    };
    private final AtomicLong accepted = new AtomicLong();
    private final AtomicLong sent = new AtomicLong();
    private final AtomicLong dropped = new AtomicLong();
    private final AtomicLong deduped = new AtomicLong();
    private final AtomicLong failed = new AtomicLong();
    private final AtomicLong skippedOff = new AtomicLong();
    private final AtomicLong skippedTool = new AtomicLong();
    private final AtomicLong skippedScope = new AtomicLong();

    private final Config settings;
    private final Log log;
    private final String userAgent;

    private volatile Thread worker;
    private volatile boolean running;
    private volatile String lastError;
    private volatile String lastResult;
    private volatile long rejectedAt = -1;
    private volatile int held;

    Sink(Config settings, Log log, String userAgent) {
        this.settings = settings;
        this.log = log;
        this.userAgent = userAgent;
    }

    void start() {
        running = true;
        worker = new Thread(this::loop, "rengine-connector-sink");
        worker.setDaemon(true);
        worker.start();
    }

    void stop() {
        running = false;
        Thread current = worker;
        if (current != null) {
            current.interrupt();
        }
    }

    /** Called on Burp's request path. Non-blocking. */
    void offer(Observation observation) {
        if (!seenRecently(observation)) {
            if (queue.offer(observation)) {
                accepted.incrementAndGet();
            } else {
                dropped.incrementAndGet();
            }
        }
    }

    private boolean seenRecently(Observation observation) {
        String key = observation.method() + " " + observation.url();
        long now = System.currentTimeMillis();
        synchronized (recent) {
            Long last = recent.get(key);
            if (last != null && now - last < RESEND_AFTER_MILLIS) {
                deduped.incrementAndGet();
                return true;
            }
            recent.put(key, now);
        }
        return false;
    }

    private void loop() {
        List<Observation> batch = null;
        int attempts = 0;
        while (running) {
            try {
                if (batch == null) {
                    Observation first = queue.poll(FLUSH_MILLIS, TimeUnit.MILLISECONDS);
                    if (first == null) {
                        continue;
                    }
                    batch = new ArrayList<>(MAX_BATCH);
                    batch.add(first);
                    queue.drainTo(batch, MAX_BATCH - 1);
                    attempts = 0;
                }
                held = batch.size();
                if (post(batch)) {
                    batch = null;
                } else if (++attempts >= MAX_ATTEMPTS) {
                    failed.addAndGet(batch.size());
                    batch = null;
                } else {
                    Thread.sleep(backoff(attempts));
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception e) {
                failed.addAndGet(batch == null ? 1 : batch.size());
                lastError = explain(e);
                batch = null;
            } finally {
                if (batch == null) {
                    held = 0;
                }
            }
        }
    }

    static long backoff(int attempts) {
        return Math.min(RETRY_MAX_MILLIS, RETRY_MIN_MILLIS << Math.min(attempts - 1, 10));
    }

    /** True when the batch is settled, false when it is held for another attempt. */
    private boolean post(List<Observation> batch) {
        if (rejectedAt == settings.generation()) {
            dropped.addAndGet(batch.size());
            return true;
        }
        if (!settings.isConfigured()) {
            dropped.addAndGet(batch.size());
            lastError = "No endpoint or token configured";
            return true;
        }
        String target = settings.targetId();
        String program = settings.programId();
        StringBuilder body = new StringBuilder("{\"client\":\"")
                .append(Json.escape(userAgent))
                .append('"');
        if (target != null && !target.isBlank()) {
            body.append(",\"target_id\":\"").append(Json.escape(target)).append('"');
        }
        if (program != null && !program.isBlank()) {
            body.append(",\"program_id\":\"").append(Json.escape(program)).append('"');
        }
        body.append(",\"items\":[");
        for (int i = 0; i < batch.size(); i++) {
            if (i > 0) {
                body.append(',');
            }
            body.append(batch.get(i).toJson());
        }
        body.append("]}");

        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(settings.endpoint()))
                    .timeout(Duration.ofSeconds(20))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + settings.token())
                    .POST(HttpRequest.BodyPublishers.ofString(body.toString()))
                    .build();
            HttpResponse<String> response = Tls.clientFor(settings)
                    .send(request, HttpResponse.BodyHandlers.ofString());
            int code = response.statusCode();
            if (code / 100 == 2) {
                String summary = summarise(response.body());
                if (summary == null) {
                    failed.addAndGet(batch.size());
                    lastError = NOT_RENGINE;
                    return true;
                }
                sent.addAndGet(batch.size());
                lastError = null;
                lastResult = summary;
                return true;
            }
            if (code == TOO_MANY_REQUESTS || code / 100 == 5) {
                lastError = refusal(response);
                return false;
            }
            failed.addAndGet(batch.size());
            if (code == UNAUTHORIZED) {
                rejectedAt = settings.generation();
                lastError = "The token was rejected. Sending is stopped.";
            } else {
                lastError = refusal(response);
            }
            return true;
        } catch (IllegalArgumentException e) {
            failed.addAndGet(batch.size());
            lastError = explain(e);
            return true;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return true;
        } catch (Exception e) {
            lastError = explain(e);
            return false;
        }
    }

    /** A response other than 2xx as a sentence. */
    static String refusal(HttpResponse<String> response) {
        int code = response.statusCode();
        if (code == UNAUTHORIZED) {
            return "The token was rejected.";
        }
        if (code / 100 == 3) {
            String to = response.headers().firstValue("Location").orElse("");
            return to.isBlank()
                    ? "The endpoint redirects elsewhere."
                    : "The endpoint redirects to " + to + ". Enter that address.";
        }
        if (code == 404 || code == 405) {
            return "No connector endpoint at this address. The path is "
                    + Settings.INGEST_PATH + ".";
        }
        if (code == TOO_MANY_REQUESTS) {
            return "reNgine is rate limiting this address.";
        }
        return "reNgine returned " + code + ".";
    }

    private static String summarise(String responseBody) {
        String accepted = Json.readString(responseBody, "accepted");
        String novel = Json.readString(responseBody, "novel");
        String recorded = Json.readString(responseBody, "recorded");
        String dropped = Json.readString(responseBody, "dropped");
        if (accepted == null) {
            return null;
        }
        return accepted + " accepted · " + novel + " new shapes · " + dropped + " discarded · "
                + (recorded == null ? "0" : recorded) + " endpoints recorded";
    }

    /** Posts an empty batch. Returns null on success. */
    String verify() {
        if (!settings.isConfigured()) {
            return "No endpoint or token configured.";
        }
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(settings.endpoint()))
                    .timeout(Duration.ofSeconds(15))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + settings.token())
                    .POST(HttpRequest.BodyPublishers.ofString(
                            "{\"client\":\"" + Json.escape(userAgent) + "\",\"items\":[]}"))
                    .build();
            HttpResponse<String> response = Tls.clientFor(settings)
                    .send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 == 2) {
                if (Json.readString(response.body(), "accepted") == null) {
                    return NOT_RENGINE;
                }
                rejectedAt = -1;
                return null;
            }
            return refusal(response);
        } catch (Exception e) {
            return explain(e);
        }
    }

    /** A connection failure as a sentence. */
    static String explain(Exception e) {
        if (e instanceof SSLHandshakeException) {
            return "The certificate was rejected. Accept a self-signed certificate "
                    + "if reNgine serves one.";
        }
        if (e instanceof SSLException) {
            return "TLS failed. Check that the endpoint serves HTTPS.";
        }
        if (e instanceof HttpConnectTimeoutException
                || e instanceof ConnectException
                || e instanceof NoRouteToHostException
                || e instanceof UnknownHostException
                || e.getCause() instanceof UnresolvedAddressException) {
            return "The endpoint could not be reached. Check the address and the port.";
        }
        if (e instanceof HttpTimeoutException) {
            return "reNgine did not answer in time.";
        }
        if (e instanceof IllegalArgumentException) {
            return "The endpoint is not a valid URL. It starts with http:// or https://.";
        }
        String message = e.getMessage();
        String name = e.getClass().getSimpleName();
        return message == null || message.isBlank() ? name : name + ": " + message;
    }

    long accepted() {
        return accepted.get();
    }

    long sent() {
        return sent.get();
    }

    long dropped() {
        return dropped.get();
    }

    long deduped() {
        return deduped.get();
    }

    long failed() {
        return failed.get();
    }

    void skippedOff() {
        skippedOff.incrementAndGet();
    }

    void skippedTool() {
        skippedTool.incrementAndGet();
    }

    void skippedScope() {
        skippedScope.incrementAndGet();
    }

    long skippedOffCount() {
        return skippedOff.get();
    }

    long skippedToolCount() {
        return skippedTool.get();
    }

    long skippedScopeCount() {
        return skippedScope.get();
    }

    int queueDepth() {
        return queue.size() + held;
    }

    String lastError() {
        return lastError;
    }

    String lastResult() {
        return lastResult;
    }

    void log(String message) {
        log.line(message);
    }
}
