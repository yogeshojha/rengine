package io.rengine.connector;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/** The target picker, read from reNgine. */
final class Targets {
    /** Nothing selected: each request is matched to a target by its hostname. */
    static final Option AUTO = new Option(null, "Match by hostname", "auto", 0, 0);

    record Option(String id, String value, String kind, int endpoints, int targets) {
        boolean isProgram() {
            return "program".equals(kind);
        }

        @Override
        public String toString() {
            if (id == null) {
                return value;
            }
            if (isProgram()) {
                return "Program: " + value + "  ·  " + targets + " target(s)";
            }
            return endpoints > 0 ? value + "  ·  " + endpoints + " endpoints scanned" : value;
        }
    }

    private final Sink.Config settings;
    private final HttpClient client;

    Targets(Sink.Config settings) {
        this.settings = settings;
        this.client = Tls.client(settings.allowSelfSigned());
    }

    static String endpointFor(String ingest) {
        String value = ingest == null ? "" : ingest.trim();
        int cut = value.lastIndexOf('/');
        return cut < 0 ? value : value.substring(0, cut) + "/targets";
    }

    List<Option> fetch() throws Exception {
        List<Option> out = new ArrayList<>();
        out.add(AUTO);
        if (!settings.isConfigured()) {
            return out;
        }
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpointFor(settings.endpoint())))
                .timeout(Duration.ofSeconds(15))
                .header("Authorization", "Bearer " + settings.token())
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() / 100 != 2) {
            return out;
        }
        out.addAll(parse(response.body()));
        return out;
    }

    private static int number(String chunk, String field) {
        String value = Json.readString(chunk, field);
        try {
            return value == null ? 0 : Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    static List<Option> parse(String body) {
        List<Option> out = new ArrayList<>();
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
            String id = Json.readString(chunk, "id");
            String value = Json.readString(chunk, "value");
            if (id == null || value == null) {
                continue;
            }
            out.add(new Option(
                    id,
                    value,
                    Json.readString(chunk, "kind"),
                    number(chunk, "endpoints"),
                    number(chunk, "targets")));
        }
        return out;
    }
}
