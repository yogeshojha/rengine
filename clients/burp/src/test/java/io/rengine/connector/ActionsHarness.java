package io.rengine.connector;

import java.util.List;

/** Checks the action wire format and endpoint derivation, without Burp. */
public final class ActionsHarness {
    private static int failed;

    public static void main(String[] args) {
        check("endpoint derives beside ingest",
                "http://h/api/v1/connectors/actions".equals(
                        Actions.endpointFor("http://h/api/v1/connectors/ingest")));
        check("endpoint tolerates a trailing form",
                "http://h/actions".equals(Actions.endpointFor("http://h/ingest")));

        List<Actions.Action> none = Actions.parse("[]");
        check("an empty array yields nothing", none.isEmpty());
        check("garbage yields nothing", Actions.parse("not json").isEmpty());
        check("null yields nothing", Actions.parse(null).isEmpty());

        List<Actions.Action> two = Actions.parse(
                "[{\"kind\":\"repeater\",\"url\":\"https://a/x?q=1\",\"method\":\"POST\",\"label\":\"/x\"},"
                        + "{\"kind\":\"repeater\",\"url\":\"https://b/y\",\"method\":\"GET\",\"label\":null}]");
        check("both actions parse", two.size() == 2);
        check("the url survives a query string", "https://a/x?q=1".equals(two.get(0).url()));
        check("the method is read", "POST".equals(two.get(0).method()));
        check("a null label is tolerated", two.get(1).label() == null);
        check("a missing method defaults to GET",
                "GET".equals(Actions.parse("[{\"url\":\"https://c/z\"}]").get(0).method()));
        check("an action with no url is dropped",
                Actions.parse("[{\"kind\":\"repeater\",\"url\":\"\"}]").isEmpty());

        check("target endpoint derives beside ingest",
                "http://h/api/v1/connectors/targets".equals(
                        Targets.endpointFor("http://h/api/v1/connectors/ingest")));
        List<Targets.Option> options = Targets.parse(
                "[{\"id\":\"11111111-1111-1111-1111-111111111111\",\"value\":\"acme.com\","
                        + "\"target_type\":\"domain\",\"kind\":\"target\",\"scanned\":true,"
                        + "\"endpoints\":47,\"targets\":0},"
                        + "{\"id\":\"22222222-2222-2222-2222-222222222222\",\"value\":\"b.io\","
                        + "\"target_type\":\"domain\",\"kind\":\"target\",\"scanned\":false,"
                        + "\"endpoints\":0,\"targets\":0},"
                        + "{\"id\":\"33333333-3333-3333-3333-333333333333\",\"value\":\"Acme BB\","
                        + "\"target_type\":\"program\",\"kind\":\"program\",\"scanned\":false,"
                        + "\"endpoints\":0,\"targets\":3}]");
        check("targets and programs parse", options.size() == 3);
        check("the endpoint count is read", options.get(0).endpoints() == 47);
        check("a target with no scan reads zero", options.get(1).endpoints() == 0);
        check("the label carries the count",
                options.get(0).toString().contains("47 endpoints scanned"));
        check("a program is recognised", options.get(2).isProgram());
        check("a target is not a program", !options.get(0).isProgram());
        check("a program label names its targets",
                options.get(2).toString().equals("Program: Acme BB  ·  3 target(s)"));
        check("auto is neither", !Targets.AUTO.isProgram());
        check("auto carries no id", Targets.AUTO.id() == null);
        check("a malformed list yields nothing", Targets.parse("{}").isEmpty());

        String scopeBody = "{\"target_value\":\"acme.com\",\"include\":[\"https://a.acme.com\","
                + "\"https://b.acme.com\"],\"exclude\":[\"https://no.acme.com\"],"
                + "\"hosts_known\":2,\"truncated\":false,\"from_program\":\"Acme BB\"}";
        check("include rules parse", Facts.strings(scopeBody, "include").size() == 2);
        check("exclude rules parse",
                Facts.strings(scopeBody, "exclude").equals(List.of("https://no.acme.com")));
        check("a missing array yields nothing", Facts.strings(scopeBody, "nope").isEmpty());
        check("an empty array yields nothing",
                Facts.strings("{\"include\":[]}", "include").isEmpty());
        check("the program name is read", "Acme BB".equals(Json.readString(scopeBody, "from_program")));
        check("a null program reads as absent",
                Json.readString("{\"from_program\":null}", "from_program") == null);

        check("notices endpoint sits beside ingest",
                "http://h/api/v1/connectors/notices".equals(
                        Actions.noticesFor("http://h/api/v1/connectors/ingest")));
        check("findings endpoint sits beside ingest",
                "http://h/api/v1/connectors/findings".equals(
                        Report.endpointFor("http://h/api/v1/connectors/ingest")));
        List<Actions.Notice> heard = Actions.parseNotices(
                "[{\"kind\":\"out_of_scope\",\"label\":\"Out of scope\","
                        + "\"url\":\"https://no.acme.com/x\",\"host\":\"no.acme.com\","
                        + "\"status_code\":200,\"seen_at\":\"2026-09-08T00:00:00Z\"},"
                        + "{\"kind\":\"sensitive\",\"label\":\"Sensitive path\","
                        + "\"url\":\"https://acme.com/.env\",\"host\":\"acme.com\","
                        + "\"status_code\":200,\"seen_at\":\"2026-09-08T00:00:00Z\"}]");
        check("both notices parse", heard.size() == 2);
        check("out of scope is recognised", heard.get(0).outOfScope());
        check("a sensitive path is not out of scope", !heard.get(1).outOfScope());
        check("an empty notice list is tolerated", Actions.parseNotices("[]").isEmpty());

        String payload = Report.body("IDOR", "https://acme.com/a", "high", "GET", "note",
                "GET /a HTTP/1.1", "HTTP/1.1 200 OK");
        check("the report carries the title", payload.contains("\"title\":\"IDOR\""));
        check("the report carries the evidence", payload.contains("\"request\":"));
        check("a report with no evidence omits it",
                !Report.body("t", "https://a/b", "low", "GET", null, null, null)
                        .contains("\"request\""));

        String raw = "[{\"kind\":\"organizer\",\"url\":\"https://a.acme.com:8443/api?q=1\","
                + "\"method\":\"POST\",\"label\":\"CVE-2021-44228\","
                + "\"request\":\"POST /api?q=1 HTTP/1.1\\r\\nHost: a.acme.com:8443\\r\\n"
                + "X-Q: \\\"quoted\\\"\\r\\n\\r\\n[{\\\"a\\\":1},{\\\"b\\\":2}]\","
                + "\"response\":\"HTTP/1.1 200 OK\\r\\n\\r\\n{}\","
                + "\"notes\":\"reNgine \\u00b7 Critical\\nline two\",\"color\":\"red\"},"
                + "{\"kind\":\"repeater\",\"url\":\"https://b.acme.com/x\",\"method\":\"GET\","
                + "\"label\":null,\"request\":null,\"response\":null,\"notes\":null,"
                + "\"color\":null}]";
        List<Actions.Action> rich = Actions.parse(raw);
        check("a request body holding },{ does not split the array", rich.size() == 2);
        check("the raw request is decoded",
                rich.get(0).request().equals("POST /api?q=1 HTTP/1.1\r\nHost: a.acme.com:8443\r\n"
                        + "X-Q: \"quoted\"\r\n\r\n[{\"a\":1},{\"b\":2}]"));
        check("the response is decoded", "HTTP/1.1 200 OK\r\n\r\n{}".equals(rich.get(0).response()));
        check("a unicode escape is decoded",
                "reNgine \u00b7 Critical\nline two".equals(rich.get(0).notes()));
        check("the colour is read", "red".equals(rich.get(0).color()));
        check("a bare action has no request", !rich.get(1).hasRequest());
        check("a bare action has no response", !rich.get(1).hasResponse());

        Handoff.Origin origin = Handoff.origin("https://a.acme.com:8443/api?q=1");
        check("the origin reads host, port and tls",
                origin.host().equals("a.acme.com") && origin.port() == 8443 && origin.secure());
        check("a plain url takes port 80",
                Handoff.origin("http://b.acme.com/x").port() == 80
                        && !Handoff.origin("http://b.acme.com/x").secure());
        check("an https url takes port 443", Handoff.origin("https://c.acme.com").port() == 443);
        check("an ipv6 literal is handed over bare",
                Handoff.origin("http://[2001:db8::1]:8080/").host().equals("2001:db8::1"));
        check("an unknown tool falls back to Repeater", Handoff.tool("scanner").equals(Handoff.REPEATER));
        check("site map is a tool", Handoff.tool("sitemap").equals(Handoff.SITE_MAP));
        check("a null tool is Repeater", Handoff.tool(null).equals(Handoff.REPEATER));

        check("a quoted value survives readString",
                "a \"b\" c".equals(Json.readString("{\"x\":\"a \\\"b\\\" c\",\"y\":1}", "x")));
        check("a nested key is not read as top level",
                Json.readString("{\"inner\":{\"x\":\"no\"},\"x\":\"yes\"}", "x").equals("yes"));
        check("a number reads as its literal", "8443".equals(Json.readString("{\"port\":8443}", "port")));
        check("a string array with commas inside values parses",
                Json.strings("{\"include\":[\"https://a/x,y\",\"https://b\"]}", "include")
                        .equals(List.of("https://a/x,y", "https://b")));

        String head = Capture.sample("GET /a?x=1 HTTP/1.1\r\nHost: h\r\nCookie: sid=1\r\n"
                + "Authorization: Bearer t\r\nX-Trace: 9\r\n\r\nbody=1");
        check("the sample keeps the request line", head.startsWith("GET /a?x=1 HTTP/1.1\r\n"));
        check("the sample masks the cookie", head.contains("Cookie: " + Capture.MASK));
        check("the sample masks authorization", head.contains("Authorization: " + Capture.MASK));
        check("the sample keeps other headers", head.contains("X-Trace: 9"));
        check("the sample drops the body", !head.contains("body=1"));
        check("the sample ends with a blank line", head.endsWith("\r\n\r\n"));
        check("an empty request has no sample", Capture.sample("") == null);

        Notices held = new Notices();
        for (int i = 0; i < Notices.KEEP + 5; i++) {
            held.add(new Actions.Notice("sensitive", "Sensitive path", "https://a/" + i, "a"));
        }
        check("the notice list is bounded", held.size() == Notices.KEEP);
        check("the newest notice is first", held.recent().get(0).url().endsWith("/16"));

        System.out.println(failed == 0 ? "all action checks passed" : failed + " failed");
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void check(String name, boolean ok) {
        System.out.println((ok ? "  PASS  " : "  FAIL  ") + name);
        if (!ok) {
            failed++;
        }
    }
}
