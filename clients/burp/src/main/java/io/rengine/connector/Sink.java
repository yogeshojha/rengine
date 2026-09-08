package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Buffers observations off the proxy thread and posts them in batches.
 *
 * <p>Nothing here touches Burp, so it can be exercised without the suite.
 */
final class Sink {
    static final int QUEUE_CAPACITY = 5000;
    static final int MAX_BATCH = 200;
    static final long FLUSH_MILLIS = 2000;
    static final int DEDUPE_CAPACITY = 20000;
    static final long RESEND_AFTER_MILLIS = 60_000;
    static final int UNAUTHORIZED = 401;

    interface Log {
        void line(String message);
    }

    /** Where to post. Kept narrow so the sink can run without Burp. */
    interface Config {
        String endpoint();

        String token();

        boolean isConfigured();

        boolean allowSelfSigned();

        /** Bumped whenever the operator saves; a client that gave up may try again. */
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
    private final HttpClient client;
    private final String userAgent;

    private volatile Thread worker;
    private volatile boolean running;
    private volatile String lastError;
    private volatile String lastResult;
    private volatile long rejectedAt = -1;

    Sink(Config settings, Log log, String userAgent) {
        this.settings = settings;
        this.log = log;
        this.userAgent = userAgent;
        this.client = Tls.client(settings.allowSelfSigned());
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

    /** Called on Burp's request path. Never blocks and never throws. */
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
        while (running) {
            try {
                Observation first = queue.poll(FLUSH_MILLIS, TimeUnit.MILLISECONDS);
                if (first == null) {
                    continue;
                }
                List<Observation> batch = new ArrayList<>(MAX_BATCH);
                batch.add(first);
                queue.drainTo(batch, MAX_BATCH - 1);
                post(batch);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception e) {
                failed.incrementAndGet();
                lastError = String.valueOf(e.getMessage());
            }
        }
    }

    private void post(List<Observation> batch) {
        if (rejectedAt == settings.generation()) {
            dropped.addAndGet(batch.size());
            return;
        }
        if (!settings.isConfigured()) {
            dropped.addAndGet(batch.size());
            lastError = "No endpoint or token configured";
            return;
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
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 == 2) {
                sent.addAndGet(batch.size());
                lastError = null;
                lastResult = summarise(response.body());
            } else if (response.statusCode() == UNAUTHORIZED) {
                failed.addAndGet(batch.size());
                rejectedAt = settings.generation();
                lastError = "The token was rejected. Sending is stopped.";
            } else {
                failed.addAndGet(batch.size());
                lastError = "reNgine returned " + response.statusCode();
            }
        } catch (Exception e) {
            failed.addAndGet(batch.size());
            lastError = explain(e);
        }
    }

    private static String summarise(String responseBody) {
        String accepted = Json.readString(responseBody, "accepted");
        String novel = Json.readString(responseBody, "novel");
        String queued = Json.readString(responseBody, "queued");
        String dropped = Json.readString(responseBody, "dropped");
        if (accepted == null) {
            return null;
        }
        return accepted + " accepted, " + novel + " new, " + dropped + " out of scope, "
                + queued + " queued";
    }

    /** Posts an empty batch to confirm the endpoint and token. Returns null when it worked. */
    String verify() {
        if (!settings.isConfigured()) {
            return "No endpoint or token configured.";
        }
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(settings.endpoint()))
                    .timeout(Duration.ofSeconds(15))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + settings.token())
                    .POST(HttpRequest.BodyPublishers.ofString("{\"client\":\"" + Json.escape(userAgent) + "\",\"items\":[]}"))
                    .build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 == 2) {
                rejectedAt = -1;
                return null;
            }
            if (response.statusCode() == UNAUTHORIZED) {
                return "The token was rejected.";
            }
            return "reNgine returned " + response.statusCode() + ".";
        } catch (Exception e) {
            return explain(e);
        }
    }

    /** The two failures a self-hosted reNgine produces, stated as facts. */
    static String explain(Exception e) {
        String name = e.getClass().getSimpleName();
        if (name.contains("SSL") || name.contains("Certificate")) {
            return "The certificate was rejected. Accept a self-signed certificate "
                    + "if reNgine serves one.";
        }
        if (name.contains("ConnectException") || name.contains("UnknownHost")
                || name.contains("HttpTimeout")) {
            return "The endpoint could not be reached: " + e.getMessage();
        }
        return name + ": " + e.getMessage();
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
        return queue.size();
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
