package io.rengine.connector;

import burp.api.montoya.persistence.Preferences;

/** Extension configuration, persisted in Burp's own preference store. */
final class Settings implements Sink.Config {
    static final String DEFAULT_ENDPOINT = "http://localhost:8000/api/v1/connectors/ingest";

    private static final String KEY_ENDPOINT = "rengine.endpoint";
    private static final String KEY_TOKEN = "rengine.token";
    private static final String KEY_ENABLED = "rengine.enabled";
    private static final String KEY_PROXY = "rengine.captureProxy";
    private static final String KEY_REPEATER = "rengine.captureRepeater";
    private static final String KEY_IN_SCOPE = "rengine.inScopeOnly";
    private static final String KEY_TITLES = "rengine.captureTitles";
    private static final String KEY_SELF_SIGNED = "rengine.allowSelfSigned";
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
            endpoint = storedEndpoint.trim();
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
        endpoint = value == null ? "" : value.trim();
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
}
