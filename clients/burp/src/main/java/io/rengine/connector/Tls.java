package io.rengine.connector;

import java.net.Socket;
import java.net.http.HttpClient;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.time.Duration;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509ExtendedTrustManager;

/** HTTP clients for the connector, including the self-signed case a self-hosted reNgine needs. */
final class Tls {
    private static volatile HttpClient cached;
    private static volatile boolean cachedPermissive;
    private static volatile boolean cachedPlain;

    private Tls() {}

    /** The client for the current settings, rebuilt when the self-signed switch or the scheme moves. */
    static HttpClient clientFor(Sink.Config settings) {
        boolean permissive = settings.allowSelfSigned();
        boolean plain = plain(settings.endpoint());
        HttpClient current = cached;
        if (current == null || cachedPermissive != permissive || cachedPlain != plain) {
            synchronized (Tls.class) {
                if (cached == null || cachedPermissive != permissive || cachedPlain != plain) {
                    cached = client(permissive, plain);
                    cachedPermissive = permissive;
                    cachedPlain = plain;
                }
                current = cached;
            }
        }
        return current;
    }

    /** HTTP/2 over TLS with HTTP/1.1 as the negotiated fallback, HTTP/1.1 over plain HTTP. */
    static HttpClient client(boolean allowSelfSigned, boolean plain) {
        HttpClient.Builder builder = HttpClient.newBuilder()
                .version(plain ? HttpClient.Version.HTTP_1_1 : HttpClient.Version.HTTP_2)
                .connectTimeout(Duration.ofSeconds(5))
                .followRedirects(HttpClient.Redirect.NEVER);
        if (allowSelfSigned) {
            SSLContext context = permissive();
            if (context != null) {
                builder.sslContext(context);
            }
        }
        return builder.build();
    }

    /** True for an endpoint without TLS. */
    static boolean plain(String endpoint) {
        return endpoint == null || !endpoint.trim().toLowerCase().startsWith("https://");
    }

    /** A context that accepts any certificate under any name. */
    private static SSLContext permissive() {
        try {
            TrustManager[] trustAll = {
                new X509ExtendedTrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {}

                    @Override
                    public void checkServerTrusted(X509Certificate[] chain, String authType) {}

                    @Override
                    public void checkClientTrusted(
                            X509Certificate[] chain, String authType, Socket socket) {}

                    @Override
                    public void checkServerTrusted(
                            X509Certificate[] chain, String authType, Socket socket) {}

                    @Override
                    public void checkClientTrusted(
                            X509Certificate[] chain, String authType, SSLEngine engine) {}

                    @Override
                    public void checkServerTrusted(
                            X509Certificate[] chain, String authType, SSLEngine engine) {}

                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[0];
                    }
                }
            };
            SSLContext context = SSLContext.getInstance("TLS");
            context.init(null, trustAll, new SecureRandom());
            return context;
        } catch (Exception e) {
            return null;
        }
    }

    /** True for plain HTTP to a remote host. */
    static boolean insecure(String endpoint) {
        String value = endpoint == null ? "" : endpoint.trim().toLowerCase();
        if (!value.startsWith("http://")) {
            return false;
        }
        String rest = value.substring("http://".length());
        if (rest.startsWith("[::1]")) {
            return false;
        }
        String host = rest.split("[:/]", 2)[0];
        return !("localhost".equals(host) || "127.0.0.1".equals(host));
    }
}
