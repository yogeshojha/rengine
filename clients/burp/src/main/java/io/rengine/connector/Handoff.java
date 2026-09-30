package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.Annotations;
import burp.api.montoya.core.ByteArray;
import burp.api.montoya.core.HighlightColor;
import burp.api.montoya.http.HttpService;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/** Opens a queued request in the Burp tool reNgine named. */
final class Handoff {
    static final String REPEATER = "repeater";
    static final String INTRUDER = "intruder";
    static final String ORGANIZER = "organizer";
    static final String SITE_MAP = "sitemap";
    static final String[] TOOLS = {REPEATER, INTRUDER, ORGANIZER, SITE_MAP};
    static final Map<String, String> TOOL_LABELS = Map.of(
            REPEATER, "Repeater",
            INTRUDER, "Intruder",
            ORGANIZER, "Organizer",
            SITE_MAP, "Site map");

    /** Where a request goes on the wire. */
    record Origin(String host, int port, boolean secure) {}

    private final MontoyaApi api;
    private final Map<String, AtomicLong> delivered = new ConcurrentHashMap<>();

    Handoff(MontoyaApi api) {
        this.api = api;
    }

    /** Host, port and TLS from a URL, the scheme's own port when none is written. */
    static Origin origin(String url) {
        URI uri = URI.create(url.trim());
        boolean secure = "https".equalsIgnoreCase(uri.getScheme());
        int port = uri.getPort() > 0 ? uri.getPort() : secure ? 443 : 80;
        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new IllegalArgumentException("No host in " + url);
        }
        if (host.startsWith("[") && host.endsWith("]")) {
            host = host.substring(1, host.length() - 1);
        }
        return new Origin(host, port, secure);
    }

    static String tool(String kind) {
        String value = kind == null ? REPEATER : kind.trim().toLowerCase(Locale.ROOT);
        for (String known : TOOLS) {
            if (known.equals(value)) {
                return known;
            }
        }
        return REPEATER;
    }

    static HighlightColor highlight(String color) {
        if (color == null || color.isBlank()) {
            return HighlightColor.NONE;
        }
        try {
            return HighlightColor.valueOf(color.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return HighlightColor.NONE;
        }
    }

    static String label(Actions.Action action) {
        String value = action.label();
        return value == null || value.isBlank() ? "reNgine" : "reNgine " + value;
    }

    void deliver(Actions.Action action) {
        Origin origin = origin(action.url());
        HttpService service = HttpService.httpService(origin.host(), origin.port(), origin.secure());
        HttpRequest request = action.hasRequest()
                ? HttpRequest.httpRequest(service, bytes(action.request()))
                : HttpRequest.httpRequestFromUrl(action.url()).withMethod(action.method());
        String tool = tool(action.kind());
        switch (tool) {
            case INTRUDER -> api.intruder().sendToIntruder(request, label(action));
            case ORGANIZER -> api.organizer().sendToOrganizer(exchange(request, action));
            case SITE_MAP -> api.siteMap().add(exchange(request, action));
            default -> api.repeater().sendToRepeater(request, label(action));
        }
        delivered.computeIfAbsent(tool, k -> new AtomicLong()).incrementAndGet();
    }

    /** The message as the UTF-8 bytes its Content-Length counts. */
    static ByteArray bytes(String message) {
        return ByteArray.byteArray(message.getBytes(StandardCharsets.UTF_8));
    }

    private static HttpRequestResponse exchange(HttpRequest request, Actions.Action action) {
        HttpResponse response = action.hasResponse()
                ? HttpResponse.httpResponse(bytes(action.response()))
                : HttpResponse.httpResponse();
        Annotations notes = action.notes() == null || action.notes().isBlank()
                ? Annotations.annotations(highlight(action.color()))
                : Annotations.annotations(action.notes(), highlight(action.color()));
        return HttpRequestResponse.httpRequestResponse(request, response, notes);
    }

    long delivered(String tool) {
        AtomicLong count = delivered.get(tool);
        return count == null ? 0 : count.get();
    }

    long delivered() {
        long total = 0;
        for (AtomicLong count : delivered.values()) {
            total += count.get();
        }
        return total;
    }

    /** One line: what reached each tool. */
    String summary() {
        StringBuilder sb = new StringBuilder();
        for (String tool : TOOLS) {
            long count = delivered(tool);
            if (count == 0) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append(" · ");
            }
            sb.append(count).append(" to ").append(TOOL_LABELS.get(tool));
        }
        return sb.toString();
    }
}
