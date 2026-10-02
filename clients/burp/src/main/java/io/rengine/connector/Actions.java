package io.rengine.connector;

import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;

/** Collects work reNgine has queued for this proxy. */
final class Actions {
    static final long POLL_MILLIS = 3000;

    /** A request reNgine queued. */
    record Action(
            String kind,
            String url,
            String label,
            String request,
            String response,
            String notes,
            String color) {
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

    private volatile Thread worker;
    private volatile boolean running;
    private volatile String lastError;
    private volatile long rejectedAt = -1;
    private volatile long lastOkAt;

    Actions(Sink.Config settings, Sink.Log log, Deliver deliver) {
        this.settings = settings;
        this.log = log;
        this.deliver = deliver;
    }

    /** The actions endpoint beside the ingest endpoint. */
    static String endpointFor(String ingest) {
        return Settings.beside(ingest, "actions");
    }

    static String noticesFor(String ingest) {
        return Settings.beside(ingest, "notices");
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
                if (settings.isConfigured() && rejectedAt != settings.generation() && collect()) {
                    collectNotices();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception e) {
                lastError = Sink.explain(e);
            }
        }
    }

    /** False when reNgine refused the request. */
    private boolean collect() throws Exception {
        HttpResponse<String> response = Tls.get(settings, endpointFor(settings.endpoint()));
        if (response.statusCode() == Sink.UNAUTHORIZED) {
            rejectedAt = settings.generation();
            lastError = "The token was rejected. Collection is stopped.";
            return false;
        }
        if (response.statusCode() / 100 != 2) {
            lastError = Sink.refusal(response);
            return false;
        }
        lastError = null;
        lastOkAt = System.currentTimeMillis();
        for (Action action : parse(response.body())) {
            try {
                deliver.action(action);
            } catch (Exception e) {
                log.line("Could not deliver an action: " + e);
            }
        }
        return true;
    }

    private void collectNotices() throws Exception {
        HttpResponse<String> response = Tls.get(settings, noticesFor(settings.endpoint()));
        if (response.statusCode() / 100 != 2) {
            return;
        }
        for (Notice notice : parseNotices(response.body())) {
            try {
                deliver.notice(notice);
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
            String request = Json.readString(chunk, "request");
            if (url == null || url.isBlank() || request == null || request.isBlank()) {
                continue;
            }
            out.add(new Action(
                    Json.readString(chunk, "kind"),
                    url,
                    Json.readString(chunk, "label"),
                    request,
                    Json.readString(chunk, "response"),
                    Json.readString(chunk, "notes"),
                    Json.readString(chunk, "color")));
        }
        return out;
    }

    String lastError() {
        return lastError;
    }

    /** True while reNgine answered a poll within the window. */
    boolean online(long withinMillis) {
        return lastOkAt > 0 && System.currentTimeMillis() - lastOkAt <= withinMillis;
    }
}
