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
