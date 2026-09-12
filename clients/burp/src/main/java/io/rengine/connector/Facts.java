package io.rengine.connector;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/** Scope rules and host facts read from reNgine. */
final class Facts {
    record Host(
            String host,
            String target,
            boolean covered,
            int known,
            int visited,
            int unvisited,
            int flagged) {}

    record Scope(List<String> include, List<String> exclude, int hostsKnown, String program) {}

    private final Sink.Config settings;
    private final HttpClient client;

    Facts(Sink.Config settings) {
        this.settings = settings;
        this.client = Tls.client(settings.allowSelfSigned());
    }

    private static String base(String ingest) {
        String value = ingest == null ? "" : ingest.trim();
        int cut = value.lastIndexOf('/');
        return cut < 0 ? value : value.substring(0, cut);
    }

    private String get(String path) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(base(settings.endpoint()) + path))
                .timeout(Duration.ofSeconds(15))
                .header("Authorization", "Bearer " + settings.token())
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.statusCode() / 100 == 2 ? response.body() : null;
    }

    Host host(String name) throws Exception {
        if (!settings.isConfigured() || name == null || name.isBlank()) {
            return null;
        }
        String body = get("/host?host=" + URLEncoder.encode(name, StandardCharsets.UTF_8));
        if (body == null) {
            return null;
        }
        return new Host(
                name,
                Json.readString(body, "target_value"),
                "true".equals(Json.readString(body, "covered")),
                number(body, "known_endpoints"),
                number(body, "visited"),
                number(body, "unvisited"),
                number(body, "flagged"));
    }

    Scope scope(String id, boolean program) throws Exception {
        if (!settings.isConfigured() || id == null || id.isBlank()) {
            return null;
        }
        String body = get("/scope?" + (program ? "program_id=" : "target_id=")
                + URLEncoder.encode(id, StandardCharsets.UTF_8));
        if (body == null) {
            return null;
        }
        return new Scope(
                strings(body, "include"),
                strings(body, "exclude"),
                number(body, "hosts_known"),
                Json.readString(body, "from_program"));
    }

    private static int number(String body, String field) {
        String value = Json.readString(body, field);
        try {
            return value == null ? 0 : Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /** Reads one flat array of strings. The response has no nested arrays. */
    static List<String> strings(String body, String field) {
        List<String> out = new ArrayList<>();
        int at = body.indexOf("\"" + field + "\":");
        if (at < 0) {
            return out;
        }
        int open = body.indexOf('[', at);
        int close = body.indexOf(']', open);
        if (open < 0 || close < 0) {
            return out;
        }
        for (String piece : body.substring(open + 1, close).split(",")) {
            String value = piece.trim();
            if (value.length() > 1 && value.startsWith("\"") && value.endsWith("\"")) {
                out.add(value.substring(1, value.length() - 1));
            }
        }
        return out;
    }
}
