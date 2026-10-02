package io.rengine.connector;

import java.net.URLEncoder;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** Scope rules and host facts read from reNgine. */
final class Facts {
    record Host(String host, String target, boolean covered, int known, int visited, int unvisited) {}

    record Scope(
            List<String> include,
            List<String> exclude,
            int hostsKnown,
            boolean truncated,
            String program) {}

    private final Sink.Config settings;

    Facts(Sink.Config settings) {
        this.settings = settings;
    }

    private String get(String path) throws Exception {
        HttpResponse<String> response =
                Tls.get(settings, Settings.beside(settings.endpoint(), path));
        return response.statusCode() / 100 == 2 ? response.body() : null;
    }

    Host host(String name) throws Exception {
        if (!settings.isConfigured() || name == null || name.isBlank()) {
            return null;
        }
        String body = get("host?host=" + URLEncoder.encode(name, StandardCharsets.UTF_8));
        if (body == null) {
            return null;
        }
        return new Host(
                name,
                Json.readString(body, "target_value"),
                "true".equals(Json.readString(body, "covered")),
                Json.integer(body, "known_endpoints"),
                Json.integer(body, "visited"),
                Json.integer(body, "unvisited"));
    }

    Scope scope(String id, boolean program) throws Exception {
        if (!settings.isConfigured() || id == null || id.isBlank()) {
            return null;
        }
        String body = get("scope?" + (program ? "program_id=" : "target_id=")
                + URLEncoder.encode(id, StandardCharsets.UTF_8));
        if (body == null) {
            return null;
        }
        return new Scope(
                Json.strings(body, "include"),
                Json.strings(body, "exclude"),
                Json.integer(body, "hosts_known"),
                "true".equals(Json.readString(body, "truncated")),
                Json.readString(body, "from_program"));
    }
}
