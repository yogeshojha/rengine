package io.rengine.connector;

import java.net.http.HttpClient;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.time.Duration;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/** HTTP clients for the connector, including the self-signed case a self-hosted reNgine needs. */
final class Tls {
    private Tls() {}

    static HttpClient client(boolean allowSelfSigned) {
        HttpClient.Builder builder = HttpClient.newBuilder()
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

    /** Accepts any certificate. Only ever reached when the operator has ticked the box. */
    private static SSLContext permissive() {
        try {
            TrustManager[] trustAll = {
                new X509TrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {}

                    @Override
                    public void checkServerTrusted(X509Certificate[] chain, String authType) {}

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

    /** True when the token would cross the network in clear text. */
    static boolean insecure(String endpoint) {
        String value = endpoint == null ? "" : endpoint.trim().toLowerCase();
        if (!value.startsWith("http://")) {
            return false;
        }
        String host = value.substring("http://".length()).split("[:/]", 2)[0];
        return !("localhost".equals(host) || "127.0.0.1".equals(host) || "[::1]".equals(host));
    }
}
