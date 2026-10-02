package io.rengine.connector;

import burp.api.montoya.persistence.Preferences;

/** Extension configuration, persisted in Burp's own preference store. */
final class Settings implements Sink.Config {
    static final String INGEST_PATH = "/api/v1/connectors/ingest";
    static final String DEFAULT_ENDPOINT = "http://localhost:8000" + INGEST_PATH;

    private static final String KEY_ENDPOINT = "rengine.endpoint";
    private static final String KEY_TOKEN = "rengine.token";
    private static final String KEY_ENABLED = "rengine.enabled";
    private static final String KEY_PROXY = "rengine.captureProxy";
    private static final String KEY_REPEATER = "rengine.captureRepeater";
    private static final String KEY_IN_SCOPE = "rengine.inScopeOnly";
    private static final String KEY_TITLES = "rengine.captureTitles";
    private static final String KEY_SELF_SIGNED = "rengine.allowSelfSigned";
    private static final String KEY_REQUEST_HEAD = "rengine.sendRequestHead";
    private static final String KEY_TARGET = "rengine.targetId";
    private static final String KEY_PROGRAM = "rengine.programId";

    private final Preferences preferences;

    private volatile String endpoint = DEFAULT_ENDPOINT;
    private volatile String token = "";
    private volatile boolean enabled = false;
    private volatile boolean captureProxy = true;
    private volatile boolean captureRepeater = true;
    private volatile boolean inScopeOnly = true;
    private volatile boolean captureTitles = true;
    private volatile boolean allowSelfSigned = false;
    private volatile boolean sendRequestHead = false;
    private volatile String targetId = null;
    private volatile String programId = null;
    private final java.util.concurrent.atomic.AtomicLong generation =
            new java.util.concurrent.atomic.AtomicLong();

    Settings(Preferences preferences) {
        this.preferences = preferences;
        load();
    }

    private void load() {
        String storedEndpoint = preferences.getString(KEY_ENDPOINT);
        if (storedEndpoint != null && !storedEndpoint.isBlank()) {
            endpoint = normalise(storedEndpoint);
        }
        String storedToken = preferences.getString(KEY_TOKEN);
        if (storedToken != null) {
            token = storedToken.trim();
        }
        enabled = bool(KEY_ENABLED, false);
        captureProxy = bool(KEY_PROXY, true);
        captureRepeater = bool(KEY_REPEATER, true);
        inScopeOnly = bool(KEY_IN_SCOPE, true);
        captureTitles = bool(KEY_TITLES, true);
        allowSelfSigned = bool(KEY_SELF_SIGNED, false);
        sendRequestHead = bool(KEY_REQUEST_HEAD, false);
        String storedTarget = preferences.getString(KEY_TARGET);
        targetId = storedTarget == null || storedTarget.isBlank() ? null : storedTarget.trim();
        String storedProgram = preferences.getString(KEY_PROGRAM);
        programId = storedProgram == null || storedProgram.isBlank() ? null : storedProgram.trim();
    }

    private boolean bool(String key, boolean fallback) {
        Boolean value = preferences.getBoolean(key);
        return value == null ? fallback : value;
    }

    @Override
    public long generation() {
        return generation.get();
    }

    void save() {
        generation.incrementAndGet();
        preferences.setString(KEY_ENDPOINT, endpoint);
        preferences.setString(KEY_TOKEN, token);
        preferences.setBoolean(KEY_ENABLED, enabled);
        preferences.setBoolean(KEY_PROXY, captureProxy);
        preferences.setBoolean(KEY_REPEATER, captureRepeater);
        preferences.setBoolean(KEY_IN_SCOPE, inScopeOnly);
        preferences.setBoolean(KEY_TITLES, captureTitles);
        preferences.setBoolean(KEY_SELF_SIGNED, allowSelfSigned);
        preferences.setBoolean(KEY_REQUEST_HEAD, sendRequestHead);
        preferences.setString(KEY_TARGET, targetId == null ? "" : targetId);
        preferences.setString(KEY_PROGRAM, programId == null ? "" : programId);
    }

    @Override
    public boolean isConfigured() {
        return !endpoint.isBlank() && !token.isBlank();
    }

    @Override
    public String endpoint() {
        return endpoint;
    }

    void endpoint(String value) {
        endpoint = normalise(value);
    }

    /** The ingest URL for what was typed: a bare origin gets the ingest path. */
    static String normalise(String value) {
        String text = value == null ? "" : value.trim();
        int scheme = text.indexOf("://");
        if (scheme < 0) {
            return text;
        }
        int slash = text.indexOf('/', scheme + 3);
        if (slash < 0) {
            return text + INGEST_PATH;
        }
        return slash == text.length() - 1 ? text.substring(0, slash) + INGEST_PATH : text;
    }

    /** The connector endpoint named {@code name} beside the ingest endpoint. */
    static String beside(String ingest, String name) {
        String value = ingest == null ? "" : ingest.trim();
        int cut = value.lastIndexOf('/');
        return cut < 0 ? value : value.substring(0, cut) + "/" + name;
    }

    @Override
    public String token() {
        return token;
    }

    void token(String value) {
        token = value == null ? "" : value.trim();
    }

    boolean enabled() {
        return enabled;
    }

    void enabled(boolean value) {
        enabled = value;
    }

    boolean captureProxy() {
        return captureProxy;
    }

    void captureProxy(boolean value) {
        captureProxy = value;
    }

    boolean captureRepeater() {
        return captureRepeater;
    }

    void captureRepeater(boolean value) {
        captureRepeater = value;
    }

    boolean inScopeOnly() {
        return inScopeOnly;
    }

    void inScopeOnly(boolean value) {
        inScopeOnly = value;
    }

    boolean captureTitles() {
        return captureTitles;
    }

    @Override
    public boolean allowSelfSigned() {
        return allowSelfSigned;
    }

    void allowSelfSigned(boolean value) {
        allowSelfSigned = value;
    }

    @Override
    public String targetId() {
        return targetId;
    }

    void targetId(String value) {
        targetId = value == null || value.isBlank() ? null : value.trim();
    }

    @Override
    public String programId() {
        return programId;
    }

    void programId(String value) {
        programId = value == null || value.isBlank() ? null : value.trim();
    }

    void captureTitles(boolean value) {
        captureTitles = value;
    }

    boolean sendRequestHead() {
        return sendRequestHead;
    }

    void sendRequestHead(boolean value) {
        sendRequestHead = value;
    }
}
