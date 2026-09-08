package io.rengine.connector;

/** Minimal JSON writer. The extension ships no dependencies. */
final class Json {
    private final StringBuilder out = new StringBuilder();
    private boolean first = true;

    static String escape(String value) {
        StringBuilder sb = new StringBuilder(value.length() + 16);
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20 || c == 0x7f) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        return sb.toString();
    }

    Json object() {
        out.append('{');
        first = true;
        return this;
    }

    Json end() {
        out.append('}');
        first = false;
        return this;
    }

    private void comma() {
        if (!first) {
            out.append(',');
        }
        first = false;
    }

    Json field(String name, String value) {
        if (value == null) {
            return this;
        }
        comma();
        out.append('"').append(escape(name)).append("\":\"").append(escape(value)).append('"');
        return this;
    }

    Json field(String name, Integer value) {
        if (value == null) {
            return this;
        }
        comma();
        out.append('"').append(escape(name)).append("\":").append(value);
        return this;
    }

    Json field(String name, boolean value) {
        comma();
        out.append('"').append(escape(name)).append("\":").append(value);
        return this;
    }

    Json raw(String name, String rawValue) {
        comma();
        out.append('"').append(escape(name)).append("\":").append(rawValue);
        return this;
    }

    static String array(java.util.List<String> values) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append('"').append(escape(values.get(i))).append('"');
        }
        return sb.append(']').toString();
    }

    /** The value of one top-level string field, or null. Enough to read the ingest response. */
    static String readString(String body, String field) {
        String needle = "\"" + field + "\":";
        int at = body.indexOf(needle);
        if (at < 0) {
            return null;
        }
        int i = at + needle.length();
        while (i < body.length() && Character.isWhitespace(body.charAt(i))) {
            i++;
        }
        if (i >= body.length()) {
            return null;
        }
        if (body.charAt(i) == '"') {
            int close = body.indexOf('"', i + 1);
            return close < 0 ? null : body.substring(i + 1, close);
        }
        int end = i;
        while (end < body.length() && "-0123456789.truefalsn".indexOf(body.charAt(end)) >= 0) {
            end++;
        }
        String literal = body.substring(i, end);
        // a JSON null is an absent value, not the text "null"
        return "null".equals(literal) ? null : literal;
    }

    @Override
    public String toString() {
        return out.toString();
    }
}
