package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.ui.contextmenu.ContextMenuEvent;
import burp.api.montoya.ui.contextmenu.ContextMenuItemsProvider;
import java.awt.Component;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.util.ArrayList;
import java.util.List;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;

/** The Report to reNgine context menu item. */
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
        JTextField title = new JTextField(44);
        JComboBox<String> severity = new JComboBox<>(SEVERITIES);
        severity.setSelectedIndex(DEFAULT_SEVERITY);
        JTextArea notes = new JTextArea(5, 44);
        notes.setLineWrap(true);
        notes.setWrapStyleWord(true);

        JPanel form = new JPanel(new GridBagLayout());
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(3, 4, 3, 4);
        c.anchor = GridBagConstraints.NORTHWEST;
        c.gridx = 0;
        c.gridy = 0;
        form.add(new JLabel("URL"), c);
        c.gridx = 1;
        form.add(new JLabel(selected.request().url()), c);
        c.gridx = 0;
        c.gridy = 1;
        form.add(new JLabel("Title"), c);
        c.gridx = 1;
        form.add(title, c);
        c.gridx = 0;
        c.gridy = 2;
        form.add(new JLabel("Severity"), c);
        c.gridx = 1;
        form.add(severity, c);
        c.gridx = 0;
        c.gridy = 3;
        form.add(new JLabel("Notes"), c);
        c.gridx = 1;
        form.add(new JScrollPane(notes), c);

        int choice = JOptionPane.showConfirmDialog(
                null, form, "Report to reNgine", JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE);
        if (choice != JOptionPane.OK_OPTION) {
            return;
        }
        if (title.getText().isBlank()) {
            JOptionPane.showMessageDialog(
                    null, "A title is required.", "Report to reNgine", JOptionPane.WARNING_MESSAGE);
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
        String heading = title.getText().trim();
        new Thread(() -> {
            String failure = report.send(payload);
            String message = failure == null
                    ? "Recorded as a finding: " + heading
                    : "Finding not recorded. " + failure;
            api.logging().logToOutput(message);
            SwingUtilities.invokeLater(() -> JOptionPane.showMessageDialog(
                    null,
                    message,
                    "Report to reNgine",
                    failure == null ? JOptionPane.INFORMATION_MESSAGE : JOptionPane.ERROR_MESSAGE));
        }, "rengine-connector-report").start();
    }
}
