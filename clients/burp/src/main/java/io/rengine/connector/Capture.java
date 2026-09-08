package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.ToolType;
import burp.api.montoya.http.handler.HttpHandler;
import burp.api.montoya.http.handler.HttpRequestToBeSent;
import burp.api.montoya.http.handler.HttpResponseReceived;
import burp.api.montoya.http.handler.RequestToBeSentAction;
import burp.api.montoya.http.handler.ResponseReceivedAction;
import burp.api.montoya.http.message.params.HttpParameterType;
import burp.api.montoya.http.message.params.ParsedHttpParameter;
import burp.api.montoya.http.message.requests.HttpRequest;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Turns responses Burp has received into observations. Runs on Burp's request path. */
final class Capture implements HttpHandler {
    static final int MAX_TITLE_BODY = 262_144;
    static final int MAX_TITLE = 300;
    static final int MAX_PARAMS = 40;
    static final int MAX_URL = 2000;

    private static final Pattern TITLE = Pattern.compile(
            "<title[^>]*>(.*?)</title>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private static final String[] AUTH_HEADERS = {
        "Authorization", "Cookie", "X-Api-Key", "X-Auth-Token", "X-CSRF-Token"
    };

    private static final Set<HttpParameterType> BODY_PARAMS = EnumSet.of(
            HttpParameterType.BODY,
            HttpParameterType.JSON,
            HttpParameterType.XML,
            HttpParameterType.MULTIPART_ATTRIBUTE);

    private final MontoyaApi api;
    private final Settings settings;
    private final Sink sink;
    private volatile String lastHost;

    Capture(MontoyaApi api, Settings settings, Sink sink) {
        this.api = api;
        this.settings = settings;
        this.sink = sink;
    }

    @Override
    public RequestToBeSentAction handleHttpRequestToBeSent(HttpRequestToBeSent request) {
        return RequestToBeSentAction.continueWith(request);
    }

    @Override
    public ResponseReceivedAction handleHttpResponseReceived(HttpResponseReceived response) {
        try {
            record(response);
        } catch (Exception e) {
            sink.log("Could not record a response: " + e);
        }
        return ResponseReceivedAction.continueWith(response);
    }

    private void record(HttpResponseReceived response) {
        if (!settings.enabled() || !settings.isConfigured()) {
            sink.skippedOff();
            return;
        }
        String tool = sourceTool(response.toolSource().toolType());
        if (tool == null) {
            sink.skippedTool();
            return;
        }
        HttpRequest request = response.initiatingRequest();
        if (request == null) {
            return;
        }
        String url = request.url();
        if (url == null || url.isBlank() || url.length() > MAX_URL) {
            return;
        }
        if (settings.inScopeOnly() && !api.scope().isInScope(url)) {
            sink.skippedScope();
            return;
        }
        lastHost = request.httpService() == null ? lastHost : url;
        sink.offer(new Observation(
                url,
                request.method(),
                (int) response.statusCode(),
                trim(response.headerValue("Content-Type"), 120),
                response.body() == null ? null : response.body().length(),
                title(response),
                authenticated(request),
                tool,
                bodyParams(request)));
    }

    /** The host most recently captured, so the tab can say what reNgine knows about it. */
    String lastHost() {
        String value = lastHost;
        if (value == null) {
            return null;
        }
        int scheme = value.indexOf("://");
        if (scheme < 0) {
            return null;
        }
        String rest = value.substring(scheme + 3);
        int cut = rest.indexOf('/');
        String authority = cut < 0 ? rest : rest.substring(0, cut);
        int port = authority.lastIndexOf(':');
        return port > 0 ? authority.substring(0, port) : authority;
    }

    private String sourceTool(ToolType type) {
        if (type == ToolType.PROXY) {
            return settings.captureProxy() ? "proxy" : null;
        }
        if (type == ToolType.REPEATER) {
            return settings.captureRepeater() ? "repeater" : null;
        }
        return null;
    }

    private static boolean authenticated(HttpRequest request) {
        for (String header : AUTH_HEADERS) {
            if (request.hasHeader(header)) {
                return true;
            }
        }
        return false;
    }

    private static List<String> bodyParams(HttpRequest request) {
        List<String> names = new ArrayList<>();
        for (ParsedHttpParameter parameter : request.parameters()) {
            if (BODY_PARAMS.contains(parameter.type())
                    && parameter.name() != null
                    && !parameter.name().isBlank()
                    && !names.contains(parameter.name())) {
                names.add(parameter.name());
                if (names.size() >= MAX_PARAMS) {
                    break;
                }
            }
        }
        return names;
    }

    private String title(HttpResponseReceived response) {
        if (!settings.captureTitles()) {
            return null;
        }
        String contentType = response.headerValue("Content-Type");
        if (contentType == null || !contentType.toLowerCase().contains("html")) {
            return null;
        }
        if (response.body() == null || response.body().length() == 0) {
            return null;
        }
        int length = Math.min(response.body().length(), MAX_TITLE_BODY);
        byte[] head = response.body().subArray(0, length).getBytes();
        Matcher matcher = TITLE.matcher(new String(head, charsetOf(contentType)));
        if (!matcher.find()) {
            return null;
        }
        String value = matcher.group(1).replaceAll("\\s+", " ").trim();
        return value.isEmpty() ? null : trim(value, MAX_TITLE);
    }

    /** Burp hands back bytes; a page's own Content-Type says how to read them. */
    private static Charset charsetOf(String contentType) {
        int at = contentType.toLowerCase().indexOf("charset=");
        if (at >= 0) {
            String name = contentType.substring(at + "charset=".length()).trim();
            int end = name.indexOf(';');
            if (end >= 0) {
                name = name.substring(0, end);
            }
            name = name.replace("\"", "").trim();
            try {
                return Charset.forName(name);
            } catch (Exception e) {
                return StandardCharsets.UTF_8;
            }
        }
        return StandardCharsets.UTF_8;
    }

    private static String trim(String value, int max) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        return trimmed.length() <= max ? trimmed : trimmed.substring(0, max);
    }
}
