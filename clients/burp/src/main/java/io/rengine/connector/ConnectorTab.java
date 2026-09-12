package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import java.awt.BorderLayout;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.ListSelectionModel;
import javax.swing.SwingUtilities;
import javax.swing.Timer;
import javax.swing.table.DefaultTableModel;

/** The reNgine tab. */
final class ConnectorTab {
    private static final int REFRESH_MILLIS = 1000;
    private static final int FACTS_MILLIS = 15_000;
    private static final String INGEST_PATH = "/api/v1/connectors/ingest";
    private static final String[] NOTICE_COLUMNS = {"Notice", "URL"};

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
    private final JCheckBox enabled = new JCheckBox("Send captured requests to reNgine");
    private final JCheckBox captureProxy = new JCheckBox("Proxy traffic");
    private final JCheckBox captureRepeater = new JCheckBox("Repeater requests");
    private final JCheckBox inScopeOnly = new JCheckBox("Only hosts in Burp's target scope");
    private final JCheckBox captureTitles = new JCheckBox("Read page titles from HTML responses");
    private final JCheckBox allowSelfSigned = new JCheckBox("Accept a self-signed certificate");
    private final JLabel status = new JLabel(" ");
    private final JLabel counters = new JLabel(" ");
    private final JLabel result = new JLabel(" ");
    private final JLabel hostLine = new JLabel(" ");
    private final JComboBox<Targets.Option> target = new JComboBox<>();
    private final DefaultTableModel noticeModel = new DefaultTableModel(NOTICE_COLUMNS, 0) {
        @Override
        public boolean isCellEditable(int row, int column) {
            return false;
        }
    };
    private final JTable noticeTable = new JTable(noticeModel);
    private List<Actions.Notice> shown = List.of();
    private Facts.Host lastFacts;

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
        form.setBorder(BorderFactory.createEmptyBorder(16, 16, 8, 16));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(3, 4, 3, 4);
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

        row = section(form, c, row, "Connection");
        row = field(form, c, row, "Endpoint", endpointField);
        row = field(form, c, row, "Token", tokenField);

        JButton save = new JButton("Save");
        save.addActionListener(e -> save());
        JButton test = new JButton("Test connection");
        test.addActionListener(e -> test());
        JButton open = new JButton("Open reNgine");
        open.addActionListener(e -> browse(webOrigin() + "/connectors"));
        row = buttons(form, c, row, save, test, open);
        row = line(form, c, row, status);

        row = gap(form, c, row);
        row = section(form, c, row, "Working on");
        target.setModel(new DefaultComboBoxModel<>(new Targets.Option[] {Targets.AUTO}));
        target.setPrototypeDisplayValue(
                new Targets.Option("x", "a-fairly-long-target-name.example.com", "target", 100000, 0));
        target.addActionListener(e -> chooseTarget());
        JButton pushScope = new JButton("Apply scope to Burp");
        pushScope.setFont(pushScope.getFont().deriveFont(Font.BOLD));
        pushScope.addActionListener(e -> applyScope());
        JButton reload = new JButton("Reload");
        reload.addActionListener(e -> loadTargets());
        JPanel picker = new JPanel();
        picker.add(target);
        picker.add(pushScope);
        picker.add(reload);
        c.gridy = row;
        c.gridx = 0;
        c.gridwidth = 2;
        form.add(picker, c);
        c.gridwidth = 1;
        row++;
        hostLine.setText("No host captured yet.");
        row = line(form, c, row, hostLine);

        row = gap(form, c, row);
        row = section(form, c, row, "Capture");
        for (JCheckBox box : new JCheckBox[] {
            enabled, captureProxy, captureRepeater, inScopeOnly, captureTitles, allowSelfSigned
        }) {
            box.addActionListener(e -> save());
            row = line(form, c, row, box);
        }

        row = gap(form, c, row);
        row = section(form, c, row, "Activity");
        row = line(form, c, row, counters);
        row = line(form, c, row, result);

        row = gap(form, c, row);
        row = section(form, c, row, "From reNgine");
        JButton openNotice = new JButton("Open in reNgine");
        openNotice.addActionListener(e -> openSelectedNotice());
        line(form, c, row, openNotice);

        noticeTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        noticeTable.setFillsViewportHeight(true);
        noticeTable.getColumnModel().getColumn(0).setPreferredWidth(200);
        noticeTable.getColumnModel().getColumn(0).setMaxWidth(260);
        noticeTable.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getClickCount() == 2) {
                    openSelectedNotice();
                }
            }
        });
        JScrollPane table = new JScrollPane(noticeTable);
        table.setBorder(BorderFactory.createEmptyBorder(0, 20, 16, 20));
        table.setPreferredSize(new Dimension(800, 220));

        root.add(form, BorderLayout.NORTH);
        root.add(table, BorderLayout.CENTER);
        api.userInterface().applyThemeToComponent(root);
        refresh();
        loadTargets();
    }

    private static int section(JPanel form, GridBagConstraints c, int row, String text) {
        JLabel label = new JLabel(text);
        label.setFont(label.getFont().deriveFont(label.getFont().getStyle() | Font.BOLD));
        c.gridy = row;
        c.gridx = 0;
        c.gridwidth = 2;
        form.add(label, c);
        c.gridwidth = 1;
        return row + 1;
    }

    private static int field(
            JPanel form, GridBagConstraints c, int row, String label, JComponent input) {
        c.gridy = row;
        c.gridx = 0;
        form.add(new JLabel(label), c);
        c.gridx = 1;
        form.add(input, c);
        return row + 1;
    }

    private static int buttons(JPanel form, GridBagConstraints c, int row, JButton... items) {
        JPanel panel = new JPanel();
        for (JButton item : items) {
            panel.add(item);
        }
        c.gridy = row;
        c.gridx = 1;
        form.add(panel, c);
        return row + 1;
    }

    private static int line(JPanel form, GridBagConstraints c, int row, JComponent item) {
        c.gridy = row;
        c.gridx = 1;
        form.add(item, c);
        return row + 1;
    }

    private static int gap(JPanel form, GridBagConstraints c, int row) {
        c.gridy = row;
        c.gridx = 0;
        form.add(Box.createVerticalStrut(10), c);
        return row + 1;
    }

    /** Web origin derived from the ingest endpoint. */
    String webOrigin() {
        String value = settings.endpoint().trim();
        int cut = value.indexOf(INGEST_PATH);
        if (cut > 0) {
            return value.substring(0, cut);
        }
        int scheme = value.indexOf("://");
        if (scheme < 0) {
            return value;
        }
        int slash = value.indexOf('/', scheme + 3);
        return slash < 0 ? value : value.substring(0, slash);
    }

    static String endpointsPage(String origin, String host) {
        return origin + "/surface/endpoints?ep_host="
                + URLEncoder.encode(host, StandardCharsets.UTF_8);
    }

    private void browse(String url) {
        try {
            if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().browse(URI.create(url));
                return;
            }
        } catch (Exception e) {
            api.logging().logToError("Could not open " + url + ": " + e);
        }
        status.setText(url);
    }

    private void openSelectedNotice() {
        int index = noticeTable.getSelectedRow();
        if (index < 0 || index >= shown.size()) {
            return;
        }
        Actions.Notice notice = shown.get(index);
        String host = notice.host() == null || notice.host().isBlank()
                ? Capture.hostOf(notice.url())
                : notice.host();
        if (host == null) {
            return;
        }
        browse(endpointsPage(webOrigin(), host));
    }

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

    private void applyScope() {
        Object selected = target.getSelectedItem();
        Targets.Option option = selected instanceof Targets.Option value ? value : null;
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
                            ? "Target added to scope. No hostnames recorded for it."
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
            SwingUtilities.invokeLater(() -> {
                lastFacts = value;
                hostLine.setText(describe(value));
            });
        }, "rengine-connector-facts").start();
    }

    static String describe(Facts.Host value) {
        if (value.target() == null) {
            return value.host() + " · not a target in this project";
        }
        if (!value.covered()) {
            return value.host() + " · " + value.target() + " · not scanned";
        }
        return value.host() + " · " + value.known() + " endpoints known · "
                + value.visited() + " opened · " + value.unvisited() + " not opened";
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

    private void renderNotices() {
        List<Actions.Notice> recent = notices.recent();
        if (recent.equals(shown)) {
            return;
        }
        shown = recent;
        noticeModel.setRowCount(0);
        for (Actions.Notice notice : recent) {
            noticeModel.addRow(new Object[] {
                notice.label() == null ? notice.kind() : notice.label(), notice.url()
            });
        }
    }

    /** Sending state. */
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
            return sink.skippedScopeCount() + " requests were outside Burp's target scope.";
        }
        if (sink.sent() == 0 && sink.skippedToolCount() > 0) {
            return sink.skippedToolCount() + " requests came from tools that are not captured.";
        }
        if (sink.lastResult() != null) {
            return "Last batch: " + sink.lastResult();
        }
        return "No traffic recorded.";
    }
}
