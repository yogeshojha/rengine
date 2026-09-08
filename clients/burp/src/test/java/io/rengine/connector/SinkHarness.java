package io.rengine.connector;

import java.util.List;

/** Drives the sink against a running reNgine, without Burp. */
public final class SinkHarness {
    public static void main(String[] args) throws Exception {
        String endpoint = args[0];
        String token = args[1];
        String host = args.length > 2 ? args[2] : "example.com";

        Sink.Config config = new Sink.Config() {
            @Override
            public String endpoint() {
                return endpoint;
            }

            @Override
            public String token() {
                return token;
            }

            @Override
            public boolean isConfigured() {
                return true;
            }

            @Override
            public boolean allowSelfSigned() {
                return false;
            }

            @Override
            public long generation() {
                return 0;
            }

            @Override
            public String targetId() {
                return null;
            }

            @Override
            public String programId() {
                return null;
            }
        };

        Sink sink = new Sink(config, System.out::println, "burp-connector/0.1.0-harness");

        String failure = sink.verify();
        System.out.println("verify: " + (failure == null ? "connected" : failure));
        if (failure != null) {
            System.exit(1);
        }

        sink.start();

        sink.offer(obs("https://" + host + "/harness/admin/", "GET", 200, "text/html", true, List.of()));
        sink.offer(obs("https://" + host + "/harness/api/orders/8812", "POST", 200, "application/json", true, List.of("amount", "reason")));
        sink.offer(obs("https://" + host + "/harness/api/orders/9931", "POST", 200, "application/json", true, List.of("amount", "reason")));
        sink.offer(obs("https://github.com/harness/settings", "GET", 200, "text/html", false, List.of()));
        // the same shape twice inside the window is held back by the client
        sink.offer(obs("https://" + host + "/harness/admin/", "GET", 200, "text/html", true, List.of()));
        // a title with characters that must survive JSON escaping
        sink.offer(new Observation(
                "https://" + host + "/harness/quote", "GET", 200, "text/html", 42,
                "He said \"hi\"\n\tand left \\ ", false, "proxy", List.of()));

        Thread.sleep(4000);

        System.out.println("accepted=" + sink.accepted()
                + " sent=" + sink.sent()
                + " deduped=" + sink.deduped()
                + " dropped=" + sink.dropped()
                + " failed=" + sink.failed());
        System.out.println("lastResult=" + sink.lastResult());
        System.out.println("lastError=" + sink.lastError());
        sink.stop();
        System.exit(sink.failed() == 0 && sink.sent() == 5 && sink.deduped() == 1 ? 0 : 1);
    }

    private static Observation obs(String url, String method, int status, String type,
            boolean authenticated, List<String> params) {
        return new Observation(url, method, status, type, 100, null, authenticated, "proxy", params);
    }
}
