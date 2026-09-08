package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/** Sends a finding a person confirmed by hand. */
final class Report {
    static final int MAX_EVIDENCE = 200_000;

    private final Sink.Config settings;
    private final HttpClient client;

    Report(Sink.Config settings) {
        this.settings = settings;
        this.client = Tls.client(settings.allowSelfSigned());
    }

    static String endpointFor(String ingest) {
        String value = ingest == null ? "" : ingest.trim();
        int cut = value.lastIndexOf('/');
        return cut < 0 ? value : value.substring(0, cut) + "/findings";
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
                .field("title", title)
                .field("url", url)
                .field("severity", severity)
                .field("method", method);
        if (notes != null && !notes.isBlank()) {
            json.field("notes", notes);
        }
        if (request != null && !request.isBlank()) {
            json.field("request", cut(request));
        }
        if (response != null && !response.isBlank()) {
            json.field("response", cut(response));
        }
        return json.end().toString();
    }

    private static String cut(String value) {
        return value.length() <= MAX_EVIDENCE ? value : value.substring(0, MAX_EVIDENCE);
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
                    client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 == 2) {
                return null;
            }
            String detail = Json.readString(response.body(), "detail");
            return detail != null ? detail : "reNgine returned " + response.statusCode() + ".";
        } catch (Exception e) {
            return Sink.explain(e);
        }
    }
}
