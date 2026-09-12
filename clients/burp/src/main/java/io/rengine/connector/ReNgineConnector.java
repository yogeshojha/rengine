package io.rengine.connector;

import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.Registration;
import burp.api.montoya.http.message.requests.HttpRequest;
import java.lang.reflect.InvocationTargetException;
import java.util.concurrent.atomic.AtomicReference;
import javax.swing.JComponent;
import javax.swing.SwingUtilities;

/** Sends requests observed in Burp to a reNgine connector. */
public class ReNgineConnector implements BurpExtension {
    static final String NAME = "reNgine Connector";
    static final String VERSION = "0.1.0";

    private Sink sink;
    private Actions actions;
    private Notices notices;
    private Registration handler;
    private Registration tab;
    private Registration menu;

    @Override
    public void initialize(MontoyaApi api) {
        api.extension().setName(NAME);

        Settings settings = new Settings(api.persistence().preferences());
        sink = new Sink(settings, api.logging()::logToOutput, "burp-connector/" + VERSION);
        sink.start();

        notices = new Notices();
        actions = new Actions(settings, api.logging()::logToOutput, new Actions.Deliver() {
            @Override
            public void action(Actions.Action action) {
                deliver(api, action);
            }

            @Override
            public void notice(Actions.Notice value) {
                notices.add(value);
                if (value.outOfScope()) {
                    api.logging().raiseErrorEvent(
                            "Out of scope for a bug bounty program: " + value.url());
                }
            }
        });
        actions.start();

        Capture capture = new Capture(api, settings, sink);
        handler = api.http().registerHttpHandler(capture);
        tab = api.userInterface()
                .registerSuiteTab("reNgine", buildTab(api, settings, sink, actions, capture, notices));

        menu = api.userInterface().registerContextMenuItemsProvider(new ReportMenu(api, settings));

        api.extension().registerUnloadingHandler(this::unload);
        api.logging().logToOutput(NAME + " " + VERSION + " loaded.");
    }

    /** Opens the action in Repeater. */
    private static void deliver(MontoyaApi api, Actions.Action action) {
        HttpRequest request = HttpRequest.httpRequestFromUrl(action.url());
        if (!"GET".equalsIgnoreCase(action.method())) {
            request = request.withMethod(action.method());
        }
        api.repeater().sendToRepeater(request, label(action));
    }

    private static String label(Actions.Action action) {
        String value = action.label();
        return value == null || value.isBlank() ? "reNgine" : "reNgine " + value;
    }

    private static JComponent buildTab(
            MontoyaApi api,
            Settings settings,
            Sink sink,
            Actions actions,
            Capture capture,
            Notices notices) {
        AtomicReference<JComponent> holder = new AtomicReference<>();
        Runnable build =
                () -> holder.set(
                        new ConnectorTab(api, settings, sink, actions, capture, notices).component());
        if (SwingUtilities.isEventDispatchThread()) {
            build.run();
        } else {
            try {
                SwingUtilities.invokeAndWait(build);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (InvocationTargetException e) {
                api.logging().logToError("Could not build the reNgine tab", e);
            }
        }
        return holder.get();
    }

    private void unload() {
        if (handler != null) {
            handler.deregister();
        }
        if (tab != null) {
            tab.deregister();
        }
        if (menu != null) {
            menu.deregister();
        }
        if (sink != null) {
            sink.stop();
        }
        if (actions != null) {
            actions.stop();
        }
    }
}
