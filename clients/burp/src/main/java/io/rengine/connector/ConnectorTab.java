package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import java.awt.BorderLayout;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;
import java.util.List;
import javax.swing.Timer;

/** The reNgine tab: connection details, what is captured, and what has been sent. */
final class ConnectorTab {
    private static final int REFRESH_MILLIS = 1000;
    private static final int FACTS_MILLIS = 15_000;

    private final MontoyaApi api;
    private final Settings settings;
    private final Sink sink;
    private final Actions actions;
    private final Targets targets;
    private final Facts facts;
    private final Capture capture;
    private final Notices notices;

    private final JPanel root = new JPanel(new BorderLayout());
    private final JTextField endpointField = new JTextField(46);
    private final JPasswordField tokenField = new JPasswordField(46);
    private final JCheckBox enabled = new JCheckBox("Send captured requests");
    private final JCheckBox captureProxy = new JCheckBox("Proxy traffic");
    private final JCheckBox captureRepeater = new JCheckBox("Repeater requests");
    private final JCheckBox inScopeOnly = new JCheckBox("Restrict to Burp's target scope");
    private final JCheckBox captureTitles = new JCheckBox("Capture page titles");
    private final JCheckBox allowSelfSigned =
            new JCheckBox("Accept a self-signed certificate");
    private final JLabel status = new JLabel(" ");
    private final JLabel counters = new JLabel(" ");
    private final JLabel result = new JLabel(" ");
    private final JLabel knownHere = new JLabel(" ");
    private final JTextArea said = new JTextArea(6, 70);
    private final JComboBox<Targets.Option> target = new JComboBox<>();

    ConnectorTab(
            MontoyaApi api,
            Settings settings,
            Sink sink,
            Actions actions,
            Capture capture,
            Notices notices) {
        this.api = api;
        this.settings = settings;
        this.sink = sink;
        this.actions = actions;
        this.targets = new Targets(settings);
        this.facts = new Facts(settings);
        this.capture = capture;
        this.notices = notices;
        build();
        new Timer(REFRESH_MILLIS, e -> refresh()).start();
        new Timer(FACTS_MILLIS, e -> refreshHostFacts()).start();
    }

    JComponent component() {
        return root;
    }

    private void build() {
        JPanel form = new JPanel(new GridBagLayout());
        form.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(4, 4, 4, 4);
        c.anchor = GridBagConstraints.WEST;
        int row = 0;

        endpointField.setText(settings.endpoint());
        tokenField.setText(settings.token());
        enabled.setSelected(settings.enabled());
        captureProxy.setSelected(settings.captureProxy());
        captureRepeater.setSelected(settings.captureRepeater());
        inScopeOnly.setSelected(settings.inScopeOnly());
        captureTitles.setSelected(settings.captureTitles());
        allowSelfSigned.setSelected(settings.allowSelfSigned());

        c.gridx = 0;
        c.gridy = row;
        form.add(heading("Connection"), c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(new JLabel("Ingest endpoint"), c);
        c.gridx = 1;
        form.add(endpointField, c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(new JLabel("Connector token"), c);
        c.gridx = 1;
        form.add(tokenField, c);
        row++;

        JButton save = new JButton("Save");
        save.addActionListener(e -> save());
        JButton test = new JButton("Test connection");
        test.addActionListener(e -> test());
        JPanel buttons = new JPanel();
        buttons.add(save);
        buttons.add(test);
        c.gridy = row;
        c.gridx = 1;
        form.add(buttons, c);
        row++;

        c.gridy = row;
        c.gridx = 1;
        form.add(status, c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(Box.createVerticalStrut(12), c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(heading("Working on"), c);
        row++;

        target.setModel(new DefaultComboBoxModel<>(new Targets.Option[] {Targets.AUTO}));
        target.addActionListener(e -> chooseTarget());
        JButton reload = new JButton("Reload targets");
        reload.addActionListener(e -> loadTargets());
        JButton pushScope = new JButton("Apply scope to Burp");
        pushScope.addActionListener(e -> applyScope());
        JPanel picker = new JPanel();
        picker.add(target);
        picker.add(reload);
        picker.add(pushScope);
        c.gridy = row;
        c.gridx = 1;
        form.add(picker, c);
        row++;

        c.gridy = row;
        c.gridx = 1;
        form.add(knownHere, c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(Box.createVerticalStrut(12), c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(heading("Capture"), c);
        row++;

        for (JCheckBox box : new JCheckBox[] {
            enabled, captureProxy, captureRepeater, inScopeOnly, captureTitles, allowSelfSigned
        }) {
            box.addActionListener(e -> save());
            c.gridy = row;
            c.gridx = 1;
            form.add(box, c);
            row++;
        }

        c.gridy = row;
        c.gridx = 0;
        form.add(Box.createVerticalStrut(12), c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(heading("Activity"), c);
        row++;

        c.gridy = row;
        c.gridx = 1;
        form.add(counters, c);
        row++;

        c.gridy = row;
        c.gridx = 1;
        form.add(result, c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(Box.createVerticalStrut(12), c);
        row++;

        c.gridy = row;
        c.gridx = 0;
        form.add(heading("From reNgine"), c);
        row++;

        said.setEditable(false);
        said.setLineWrap(false);
        said.setText("Nothing yet.");
        c.gridy = row;
        c.gridx = 1;
        form.add(new JScrollPane(said), c);

        root.add(form, BorderLayout.NORTH);
        api.userInterface().applyThemeToComponent(root);
        refresh();
        loadTargets();
    }

    private static JLabel heading(String text) {
        JLabel label = new JLabel(text);
        label.setFont(label.getFont().deriveFont(label.getFont().getStyle() | java.awt.Font.BOLD));
        return label;
    }

    /** The picker is filled from reNgine over the same connection the observations use. */
    private void loadTargets() {
        new Thread(() -> {
            List<Targets.Option> options;
            try {
                options = targets.fetch();
            } catch (Exception e) {
                options = List.of(Targets.AUTO);
            }
            List<Targets.Option> loaded = options;
            SwingUtilities.invokeLater(() -> {
                target.setModel(new DefaultComboBoxModel<>(loaded.toArray(new Targets.Option[0])));
                String chosen = settings.targetId();
                String chosenProgram = settings.programId();
                for (Targets.Option option : loaded) {
                    boolean match = option.isProgram()
                            ? chosenProgram != null && chosenProgram.equals(option.id())
                            : chosen != null && chosen.equals(option.id());
                    if (match) {
                        target.setSelectedItem(option);
                        return;
                    }
                }
                target.setSelectedItem(Targets.AUTO);
            });
        }, "rengine-connector-targets").start();
    }

    /** reNgine knows the hostnames; Burp's scope is set from them. */
    private void applyScope() {
        Object selected = target.getSelectedItem();
        Targets.Option option =
                selected instanceof Targets.Option value ? value : null;
        if (option == null || option.id() == null) {
            status.setText("Choose a target or a program first.");
            return;
        }
        status.setText("Applying scope…");
        new Thread(() -> {
            String message;
            try {
                Facts.Scope scope = facts.scope(option.id(), option.isProgram());
                if (scope == null) {
                    message = "Scope could not be read.";
                } else {
                    for (String url : scope.include()) {
                        api.scope().includeInScope(url);
                    }
                    for (String url : scope.exclude()) {
                        api.scope().excludeFromScope(url);
                    }
                    message = scope.hostsKnown() == 0
                            ? "Only the target itself was added. No scan has covered it yet."
                            : scope.include().size() + " hosts added to scope"
                                    + (scope.exclude().isEmpty()
                                            ? ""
                                            : ", " + scope.exclude().size() + " excluded")
                                    + (scope.program() == null ? "" : " · " + scope.program());
                }
            } catch (Exception e) {
                message = Sink.explain(e);
            }
            String text = message;
            SwingUtilities.invokeLater(() -> status.setText(text));
        }, "rengine-connector-scope").start();
    }

    private void refreshHostFacts() {
        String host = capture.lastHost();
        if (host == null || !settings.isConfigured()) {
            return;
        }
        new Thread(() -> {
            Facts.Host known;
            try {
                known = facts.host(host);
            } catch (Exception e) {
                known = null;
            }
            if (known == null) {
                return;
            }
            Facts.Host value = known;
            SwingUtilities.invokeLater(() -> knownHere.setText(
                    value.known() == 0
                            ? value.host() + " · no scan has covered this host yet"
                            : value.host() + " · " + value.known() + " endpoints known · "
                                    + value.visited() + " reached · " + value.unvisited()
                                    + " not opened"));
        }, "rengine-connector-facts").start();
    }

    private void chooseTarget() {
        Object selected = target.getSelectedItem();
        if (selected instanceof Targets.Option option) {
            settings.targetId(option.isProgram() ? null : option.id());
            settings.programId(option.isProgram() ? option.id() : null);
            settings.save();
        }
    }

    private void save() {
        settings.endpoint(endpointField.getText());
        settings.token(new String(tokenField.getPassword()));
        settings.enabled(enabled.isSelected());
        settings.captureProxy(captureProxy.isSelected());
        settings.captureRepeater(captureRepeater.isSelected());
        settings.inScopeOnly(inScopeOnly.isSelected());
        settings.captureTitles(captureTitles.isSelected());
        settings.allowSelfSigned(allowSelfSigned.isSelected());
        settings.save();
        status.setText("Saved.");
        loadTargets();
    }

    private void test() {
        save();
        status.setText("Testing…");
        new Thread(() -> {
            String failure = sink.verify();
            SwingUtilities.invokeLater(() ->
                    status.setText(failure == null ? "Connected." : failure));
        }, "rengine-connector-test").start();
    }

    private void refresh() {
        counters.setText(String.format(
                "%d sent · %d queued · %d repeated · %d dropped · %d failed · %d to Repeater",
                sink.sent(), sink.queueDepth(), sink.deduped(), sink.dropped(), sink.failed(),
                actions.delivered()));
        result.setText(explain());
        renderNotices();
    }

    /** The last few things reNgine said, so the tester never has to go and look. */
    private void renderNotices() {
        List<Actions.Notice> recent = notices.recent();
        if (recent.isEmpty()) {
            said.setText("Nothing yet.");
            return;
        }
        StringBuilder text = new StringBuilder();
        for (Actions.Notice notice : recent) {
            text.append(notice.outOfScope() ? "!! " : "   ")
                    .append(notice.label() == null ? notice.kind() : notice.label())
                    .append("  ")
                    .append(notice.url())
                    .append(System.lineSeparator());
        }
        said.setText(text.toString());
        said.setCaretPosition(0);
    }

    /** Says why nothing is being sent, rather than leaving the counters at zero unexplained. */
    private String explain() {
        String error = sink.lastError();
        if (error != null) {
            return error;
        }
        if (!settings.isConfigured()) {
            return "No endpoint or token configured.";
        }
        if (Tls.insecure(settings.endpoint())) {
            return "The endpoint is plain HTTP. The token is sent unencrypted.";
        }
        if (!settings.enabled()) {
            return "Capture is off.";
        }
        if (sink.sent() == 0 && sink.skippedScopeCount() > 0) {
            return sink.skippedScopeCount()
                    + " requests were outside Burp's target scope.";
        }
        if (sink.sent() == 0 && sink.skippedToolCount() > 0) {
            return sink.skippedToolCount()
                    + " requests came from tools that are not captured.";
        }
        if (sink.lastResult() != null) {
            return "Last batch: " + sink.lastResult();
        }
        return "No traffic recorded.";
    }
}
