package io.rengine.connector;

import java.net.http.HttpResponse;
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
                return "Program: " + value + "  ·  " + targets
                        + (targets == 1 ? " target" : " targets");
            }
            return endpoints > 0 ? value + "  ·  " + endpoints + " endpoints scanned" : value;
        }
    }

    /** The target list was refused. */
    static final class Refused extends Exception {
        private static final long serialVersionUID = 1L;

        Refused(String message) {
            super(message);
        }
    }

    private final Sink.Config settings;

    Targets(Sink.Config settings) {
        this.settings = settings;
    }

    static String endpointFor(String ingest) {
        return Settings.beside(ingest, "targets");
    }

    List<Option> fetch() throws Exception {
        List<Option> out = new ArrayList<>();
        out.add(AUTO);
        if (!settings.isConfigured()) {
            return out;
        }
        HttpResponse<String> response = Tls.get(settings, endpointFor(settings.endpoint()));
        if (response.statusCode() / 100 != 2) {
            throw new Refused(Sink.refusal(response));
        }
        out.addAll(parse(response.body()));
        return out;
    }

    static List<Option> parse(String body) {
        List<Option> out = new ArrayList<>();
        if (body == null) {
            return out;
        }
        for (String chunk : Json.objects(body)) {
            String id = Json.readString(chunk, "id");
            String value = Json.readString(chunk, "value");
            if (id == null || value == null) {
                continue;
            }
            out.add(new Option(
                    id,
                    value,
                    Json.readString(chunk, "kind"),
                    Json.integer(chunk, "endpoints"),
                    Json.integer(chunk, "targets")));
        }
        return out;
    }
}
