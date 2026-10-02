package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/** Sends a finding a person confirmed by hand. */
final class Report {
    static final int MAX_EVIDENCE = 200_000;
    static final int MAX_TITLE = 500;
    static final int MAX_NOTES = 8000;
    static final int MAX_URL = 2000;
    static final int MAX_METHOD = 16;

    private final Sink.Config settings;

    Report(Sink.Config settings) {
        this.settings = settings;
    }

    static String endpointFor(String ingest) {
        return Settings.beside(ingest, "findings");
    }

    static String body(
            String title,
            String url,
            String severity,
            String method,
            String notes,
            String request,
            String response) {
        Json json = new Json().object()
                .field("title", cut(title, MAX_TITLE))
                .field("url", url)
                .field("severity", severity)
                .field("method", method == null ? null : cut(method, MAX_METHOD));
        if (notes != null && !notes.isBlank()) {
            json.field("notes", cut(notes, MAX_NOTES));
        }
        if (request != null && !request.isBlank()) {
            json.field("request", cut(request, MAX_EVIDENCE));
        }
        if (response != null && !response.isBlank()) {
            json.field("response", cut(response, MAX_EVIDENCE));
        }
        return json.end().toString();
    }

    private static String cut(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }

    /** Returns null when it worked, otherwise what to tell the tester. */
    String send(String payload) {
        if (!settings.isConfigured()) {
            return "No endpoint or token configured.";
        }
        try {
            HttpRequest request = HttpRequest.newBuilder(
                            URI.create(endpointFor(settings.endpoint())))
                    .timeout(Duration.ofSeconds(20))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + settings.token())
                    .POST(HttpRequest.BodyPublishers.ofString(payload))
                    .build();
            HttpResponse<String> response =
                    Tls.clientFor(settings).send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 == 2) {
                return null;
            }
            String detail = Json.readString(response.body(), "detail");
            return detail != null && !detail.isBlank() ? detail : Sink.refusal(response);
        } catch (Exception e) {
            return Sink.explain(e);
        }
    }
}
