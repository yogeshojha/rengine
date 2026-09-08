package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.ui.contextmenu.ContextMenuEvent;
import burp.api.montoya.ui.contextmenu.ContextMenuItemsProvider;
import java.awt.Component;
import java.util.ArrayList;
import java.util.List;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JTextField;

/** Right-click a request, report what you found. The evidence comes with it. */
final class ReportMenu implements ContextMenuItemsProvider {
    private static final String[] SEVERITIES = {"critical", "high", "medium", "low", "info"};
    private static final int DEFAULT_SEVERITY = 2;

    private final MontoyaApi api;
    private final Report report;

    ReportMenu(MontoyaApi api, Sink.Config settings) {
        this.api = api;
        this.report = new Report(settings);
    }

    @Override
    public List<Component> provideMenuItems(ContextMenuEvent event) {
        HttpRequestResponse selected = pick(event);
        if (selected == null || selected.request() == null) {
            return List.of();
        }
        JMenuItem item = new JMenuItem("Report to reNgine");
        item.addActionListener(e -> ask(selected));
        List<Component> items = new ArrayList<>();
        items.add(item);
        return items;
    }

    private static HttpRequestResponse pick(ContextMenuEvent event) {
        if (!event.selectedRequestResponses().isEmpty()) {
            return event.selectedRequestResponses().get(0);
        }
        return event.messageEditorRequestResponse()
                .map(editor -> editor.requestResponse())
                .orElse(null);
    }

    private void ask(HttpRequestResponse selected) {
        JTextField title = new JTextField(40);
        JComboBox<String> severity = new JComboBox<>(SEVERITIES);
        severity.setSelectedIndex(DEFAULT_SEVERITY);
        JTextField notes = new JTextField(40);
        JPanel form = new JPanel();
        form.add(new JLabel("What did you find?"));
        form.add(title);
        form.add(new JLabel("Severity"));
        form.add(severity);
        form.add(new JLabel("Notes"));
        form.add(notes);

        int choice = JOptionPane.showConfirmDialog(
                null, form, "Report to reNgine", JOptionPane.OK_CANCEL_OPTION);
        if (choice != JOptionPane.OK_OPTION || title.getText().isBlank()) {
            return;
        }
        String payload = Report.body(
                title.getText().trim(),
                selected.request().url(),
                String.valueOf(severity.getSelectedItem()),
                selected.request().method(),
                notes.getText().trim(),
                selected.request().toString(),
                selected.response() == null ? null : selected.response().toString());
        new Thread(() -> {
            String failure = report.send(payload);
            api.logging().logToOutput(
                    failure == null
                            ? "Reported to reNgine: " + title.getText().trim()
                            : "Could not report: " + failure);
        }, "rengine-connector-report").start();
    }
}
