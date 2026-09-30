package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** Collects work reNgine has queued for this proxy. */
final class Actions {
    static final long POLL_MILLIS = 3000;
    static final int UNAUTHORIZED = 401;

    /** A request reNgine queued: the raw message when one was stored, else the URL and method. */
    record Action(
            String kind,
            String url,
            String method,
            String label,
            String request,
            String response,
            String notes,
            String color) {
        Action(String kind, String url, String method, String label) {
            this(kind, url, method, label, null, null, null, null);
        }

        boolean hasRequest() {
            return request != null && !request.isBlank();
        }

        boolean hasResponse() {
            return response != null && !response.isBlank();
        }
    }

    /** A notice from reNgine. */
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
    }

    /** The actions endpoint beside the ingest endpoint. */
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
        HttpResponse<String> response = Tls.clientFor(settings)
                .send(request, HttpResponse.BodyHandlers.ofString());
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
        HttpResponse<String> response = Tls.clientFor(settings)
                .send(request, HttpResponse.BodyHandlers.ofString());
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
        for (String chunk : Json.objects(body)) {
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

    /** Parses a flat array of flat objects. */
    static List<Action> parse(String body) {
        List<Action> out = new ArrayList<>();
        for (String chunk : Json.objects(body)) {
            String url = Json.readString(chunk, "url");
            if (url == null || url.isBlank()) {
                continue;
            }
            String method = Json.readString(chunk, "method");
            out.add(new Action(
                    Json.readString(chunk, "kind"),
                    url,
                    method == null || method.isBlank() ? "GET" : method,
                    Json.readString(chunk, "label"),
                    Json.readString(chunk, "request"),
                    Json.readString(chunk, "response"),
                    Json.readString(chunk, "notes"),
                    Json.readString(chunk, "color")));
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
