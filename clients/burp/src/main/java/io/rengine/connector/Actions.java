package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Collects work reNgine has queued for this proxy.
 *
 * <p>The proxy asks; reNgine never pushes. Nothing here touches Burp, so delivery is a callback.
 */
final class Actions {
    static final long POLL_MILLIS = 3000;
    static final int UNAUTHORIZED = 401;

    record Action(String kind, String url, String method, String label) {}

    /** Something reNgine wants the tester to know while they are still testing. */
    record Notice(String kind, String label, String url, String host) {
        boolean outOfScope() {
            return "out_of_scope".equals(kind);
        }
    }

    interface Deliver {
        void action(Action action);

        void notice(Notice notice);
    }

    private final Sink.Config settings;
    private final Sink.Log log;
    private final Deliver deliver;
    private final HttpClient client;
    private final AtomicLong delivered = new AtomicLong();
    private final AtomicLong noticed = new AtomicLong();

    private volatile Thread worker;
    private volatile boolean running;
    private volatile String lastError;
    private volatile long rejectedAt = -1;

    Actions(Sink.Config settings, Sink.Log log, Deliver deliver) {
        this.settings = settings;
        this.log = log;
        this.deliver = deliver;
        this.client = Tls.client(settings.allowSelfSigned());
    }

    /** The ingest endpoint names the instance; actions sit beside it. */
    static String endpointFor(String ingest) {
        return beside(ingest, "actions");
    }

    static String noticesFor(String ingest) {
        return beside(ingest, "notices");
    }

    private static String beside(String ingest, String name) {
        String value = ingest == null ? "" : ingest.trim();
        int cut = value.lastIndexOf('/');
        return cut < 0 ? value : value.substring(0, cut) + "/" + name;
    }

    void start() {
        running = true;
        worker = new Thread(this::loop, "rengine-connector-actions");
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

    private void loop() {
        while (running) {
            try {
                Thread.sleep(POLL_MILLIS);
                if (settings.isConfigured() && rejectedAt != settings.generation()) {
                    collect();
                    collectNotices();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception e) {
                lastError = e.getClass().getSimpleName() + ": " + e.getMessage();
            }
        }
    }

    private void collect() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpointFor(settings.endpoint())))
                .timeout(Duration.ofSeconds(15))
                .header("Authorization", "Bearer " + settings.token())
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() == UNAUTHORIZED) {
            rejectedAt = settings.generation();
            lastError = "The token was rejected. Collection is stopped.";
            return;
        }
        if (response.statusCode() / 100 != 2) {
            lastError = "reNgine returned " + response.statusCode() + " for actions";
            return;
        }
        lastError = null;
        for (Action action : parse(response.body())) {
            try {
                deliver.action(action);
                delivered.incrementAndGet();
            } catch (Exception e) {
                log.line("Could not deliver an action: " + e);
            }
        }
    }

    private void collectNotices() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(noticesFor(settings.endpoint())))
                .timeout(Duration.ofSeconds(15))
                .header("Authorization", "Bearer " + settings.token())
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() / 100 != 2) {
            return;
        }
        for (Notice notice : parseNotices(response.body())) {
            try {
                deliver.notice(notice);
                noticed.incrementAndGet();
            } catch (Exception e) {
                log.line("Could not show a notice: " + e);
            }
        }
    }

    static List<Notice> parseNotices(String body) {
        List<Notice> out = new ArrayList<>();
        for (String chunk : chunks(body)) {
            String url = Json.readString(chunk, "url");
            if (url == null || url.isBlank()) {
                continue;
            }
            out.add(new Notice(
                    Json.readString(chunk, "kind"),
                    Json.readString(chunk, "label"),
                    url,
                    Json.readString(chunk, "host")));
        }
        return out;
    }

    private static List<String> chunks(String body) {
        List<String> out = new ArrayList<>();
        if (body == null) {
            return out;
        }
        String trimmed = body.trim();
        int open = trimmed.indexOf('[');
        int close = trimmed.lastIndexOf(']');
        if (open < 0 || close <= open) {
            return out;
        }
        String inner = trimmed.substring(open + 1, close).trim();
        if (inner.isEmpty()) {
            return out;
        }
        for (String chunk : inner.split("(?<=\\})\\s*,\\s*(?=\\{)")) {
            out.add(chunk);
        }
        return out;
    }

    /** The response is a flat array of flat objects; a JSON dependency is not worth it. */
    static List<Action> parse(String body) {
        List<Action> out = new ArrayList<>();
        if (body == null) {
            return out;
        }
        for (String chunk : chunks(body)) {
            String url = Json.readString(chunk, "url");
            if (url == null || url.isBlank()) {
                continue;
            }
            String method = Json.readString(chunk, "method");
            out.add(new Action(
                    Json.readString(chunk, "kind"),
                    url,
                    method == null || method.isBlank() ? "GET" : method,
                    Json.readString(chunk, "label")));
        }
        return out;
    }

    long delivered() {
        return delivered.get();
    }

    long noticed() {
        return noticed.get();
    }

    String lastError() {
        return lastError;
    }
}
