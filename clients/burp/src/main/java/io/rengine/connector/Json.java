package io.rengine.connector;

import java.util.ArrayList;
import java.util.List;

/** Minimal JSON writer and reader for flat objects. The extension ships no dependencies. */
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

    /** The value of one top-level field: a decoded string, a bare literal, or null. */
    static String readString(String body, String field) {
        int at = fieldStart(body, field);
        if (at < 0) {
            return null;
        }
        if (body.charAt(at) == '"') {
            StringBuilder sb = new StringBuilder();
            readInto(body, at, sb);
            return sb.toString();
        }
        int end = at;
        while (end < body.length() && "-0123456789.truefalsn".indexOf(body.charAt(end)) >= 0) {
            end++;
        }
        String literal = body.substring(at, end);
        return "null".equals(literal) ? null : literal;
    }

    /** One flat array of strings. */
    static List<String> strings(String body, String field) {
        List<String> out = new ArrayList<>();
        int at = fieldStart(body, field);
        if (at < 0 || body.charAt(at) != '[') {
            return out;
        }
        int i = at + 1;
        while (i < body.length()) {
            char c = body.charAt(i);
            if (c == ']') {
                return out;
            }
            if (c == '"') {
                StringBuilder sb = new StringBuilder();
                i = readInto(body, i, sb);
                out.add(sb.toString());
                continue;
            }
            i++;
        }
        return out;
    }

    /** Each object of a top-level array, as its own text. */
    static List<String> objects(String body) {
        List<String> out = new ArrayList<>();
        if (body == null) {
            return out;
        }
        int open = body.indexOf('[');
        if (open < 0) {
            return out;
        }
        int depth = 0;
        int start = -1;
        boolean inString = false;
        for (int i = open + 1; i < body.length(); i++) {
            char c = body.charAt(i);
            if (inString) {
                if (c == '\\') {
                    i++;
                } else if (c == '"') {
                    inString = false;
                }
                continue;
            }
            if (c == '"') {
                inString = true;
            } else if (c == '{') {
                if (depth == 0) {
                    start = i;
                }
                depth++;
            } else if (c == '}') {
                depth--;
                if (depth == 0 && start >= 0) {
                    out.add(body.substring(start, i + 1));
                    start = -1;
                }
            } else if (c == ']' && depth == 0) {
                break;
            }
        }
        return out;
    }

    /** Index of the value that follows the named top-level key, or -1. */
    private static int fieldStart(String body, String field) {
        if (body == null) {
            return -1;
        }
        String key = "\"" + field + "\"";
        int from = 0;
        int depth = 0;
        boolean inString = false;
        for (int i = 0; i < body.length(); i++) {
            char c = body.charAt(i);
            if (inString) {
                if (c == '\\') {
                    i++;
                } else if (c == '"') {
                    inString = false;
                }
                continue;
            }
            if (c == '{' || c == '[') {
                depth++;
            } else if (c == '}' || c == ']') {
                depth--;
            } else if (c == '"') {
                if (depth == 1 && body.startsWith(key, i)) {
                    from = i + key.length();
                    while (from < body.length() && Character.isWhitespace(body.charAt(from))) {
                        from++;
                    }
                    if (from < body.length() && body.charAt(from) == ':') {
                        from++;
                        while (from < body.length()
                                && Character.isWhitespace(body.charAt(from))) {
                            from++;
                        }
                        return from < body.length() ? from : -1;
                    }
                }
                inString = true;
            }
        }
        return -1;
    }

    /** Decodes the string at the opening quote; returns the index after the closing one. */
    private static int readInto(String body, int at, StringBuilder sb) {
        int i = at + 1;
        while (i < body.length()) {
            char c = body.charAt(i);
            if (c == '"') {
                return i + 1;
            }
            if (c == '\\' && i + 1 < body.length()) {
                char e = body.charAt(++i);
                switch (e) {
                    case 'n' -> sb.append('\n');
                    case 'r' -> sb.append('\r');
                    case 't' -> sb.append('\t');
                    case 'b' -> sb.append('\b');
                    case 'f' -> sb.append('\f');
                    case 'u' -> {
                        if (i + 4 < body.length()) {
                            sb.append((char) Integer.parseInt(body.substring(i + 1, i + 5), 16));
                            i += 4;
                        }
                    }
                    default -> sb.append(e);
                }
                i++;
                continue;
            }
            sb.append(c);
            i++;
        }
        return i;
    }

    @Override
    public String toString() {
        return out.toString();
    }
}
