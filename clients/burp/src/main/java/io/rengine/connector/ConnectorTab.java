package io.rengine.connector;

import burp.api.montoya.MontoyaApi;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JScrollPane;
import javax.swing.JSeparator;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.ListSelectionModel;
import javax.swing.SwingUtilities;
import javax.swing.Timer;
import javax.swing.UIManager;
import javax.swing.table.DefaultTableModel;

/** The reNgine tab. */
final class ConnectorTab {
    private static final int REFRESH_MILLIS = 1000;
    private static final int FACTS_MILLIS = 15_000;
    private static final long ONLINE_MILLIS = 10_000;
    private static final int FIELD_COLUMNS = 20;
    private static final int LEFT_WIDTH = 520;
    private static final String[] NOTICE_COLUMNS = {"Notice", "URL"};
    private static final String[] COUNTERS = {"Sent", "Queued", "Repeated", "Dropped", "Failed"};
    private static final Color OK = new Color(0x2E9E5B);
    private static final Color FAIL = new Color(0xD64545);
    private static final Color WARN = new Color(0xC98A1B);

    private final MontoyaApi api;
    private final Settings settings;
    private final Sink sink;
    private final Actions actions;
    private final Handoff handoff;
    private final Targets targets;
    private final Facts facts;
    private final Capture capture;
    private final Notices notices;

    private final JPanel root = new JPanel(new BorderLayout());
    private final JLabel dot = new JLabel("\u25CF");
    private final JLabel state = new JLabel("Not configured");
    private final JLabel stateDetail = new JLabel(" ");
    private final JTextField endpointField = new JTextField(FIELD_COLUMNS);
    private final JPasswordField tokenField = new JPasswordField(FIELD_COLUMNS);
    private final JCheckBox enabled = new JCheckBox("Send captured requests to reNgine");
    private final JCheckBox captureProxy = new JCheckBox("Proxy");
    private final JCheckBox captureRepeater = new JCheckBox("Repeater");
    private final JCheckBox inScopeOnly = new JCheckBox("Only hosts in Burp's target scope");
    private final JCheckBox captureTitles = new JCheckBox("Read page titles from HTML responses");
    private final JCheckBox sendRequestHead =
            new JCheckBox("Send request headers. Credential values are masked.");
    private final JCheckBox allowSelfSigned = new JCheckBox("Accept a self-signed certificate");
    private final JButton saveAndTest = new JButton("Save and test");
    private final JLabel status = new JLabel(" ");
    private final JLabel[] counts = new JLabel[COUNTERS.length];
    private final JLabel received = new JLabel(" ");
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
    private final Timer refreshTimer = new Timer(REFRESH_MILLIS, e -> refresh());
    private final Timer factsTimer = new Timer(FACTS_MILLIS, e -> refreshHostFacts());
    private List<Actions.Notice> shown = List.of();
    private Color muted = Color.GRAY;
    private Color plain = Color.BLACK;

    ConnectorTab(
            MontoyaApi api,
            Settings settings,
            Sink sink,
            Actions actions,
            Handoff handoff,
            Capture capture,
            Notices notices) {
        this.api = api;
        this.settings = settings;
        this.sink = sink;
        this.actions = actions;
        this.handoff = handoff;
        this.targets = new Targets(settings);
        this.facts = new Facts(settings);
        this.capture = capture;
        this.notices = notices;
        build();
        refreshTimer.start();
        factsTimer.start();
    }

    /** Stops the timers when the extension unloads. */
    void dispose() {
        refreshTimer.stop();
        factsTimer.stop();
    }

    JComponent component() {
        return root;
    }

    private void build() {
        endpointField.setText(settings.endpoint());
        tokenField.setText(settings.token());
        enabled.setSelected(settings.enabled());
        captureProxy.setSelected(settings.captureProxy());
        captureRepeater.setSelected(settings.captureRepeater());
        inScopeOnly.setSelected(settings.inScopeOnly());
        captureTitles.setSelected(settings.captureTitles());
        sendRequestHead.setSelected(settings.sendRequestHead());
        allowSelfSigned.setSelected(settings.allowSelfSigned());

        JPanel left = new JPanel();
        left.setLayout(new BoxLayout(left, BoxLayout.Y_AXIS));
        left.setBorder(BorderFactory.createEmptyBorder(4, 20, 16, 12));
        left.add(connection());
        left.add(Box.createVerticalStrut(18));
        left.add(workingOn());
        left.add(Box.createVerticalStrut(18));
        left.add(captureSection());
        JPanel leftHolder = new JPanel(new BorderLayout());
        leftHolder.add(left, BorderLayout.NORTH);
        leftHolder.setPreferredSize(new Dimension(LEFT_WIDTH, 10));

        JPanel right = new JPanel(new BorderLayout());
        right.setBorder(BorderFactory.createEmptyBorder(4, 12, 16, 20));
        right.add(activity(), BorderLayout.NORTH);
        right.add(fromReNgine(), BorderLayout.CENTER);

        root.add(header(), BorderLayout.NORTH);
        root.add(leftHolder, BorderLayout.WEST);
        root.add(right, BorderLayout.CENTER);
        api.userInterface().applyThemeToComponent(root);
        style();
        refresh();
        loadTargets();
    }

    /** Fonts and colours set after Burp themes the tree. */
    private void style() {
        Color disabled = UIManager.getColor("Label.disabledForeground");
        muted = disabled == null ? Color.GRAY : disabled;
        plain = state.getForeground();
        state.setFont(state.getFont().deriveFont(Font.BOLD, state.getFont().getSize2D() + 3f));
        dot.setFont(state.getFont());
        stateDetail.setForeground(muted);
        hostLine.setForeground(muted);
        received.setForeground(muted);
        saveAndTest.setFont(saveAndTest.getFont().deriveFont(Font.BOLD));
        enabled.setFont(enabled.getFont().deriveFont(Font.BOLD));
        for (JLabel count : counts) {
            count.setFont(count.getFont().deriveFont(Font.BOLD, count.getFont().getSize2D() + 6f));
        }
    }

    private JComponent header() {
        JPanel text = new JPanel();
        text.setLayout(new BoxLayout(text, BoxLayout.Y_AXIS));
        JPanel line = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 0));
        line.add(dot);
        line.add(state);
        line.setAlignmentX(Component.LEFT_ALIGNMENT);
        stateDetail.setBorder(BorderFactory.createEmptyBorder(2, 8, 0, 0));
        stateDetail.setAlignmentX(Component.LEFT_ALIGNMENT);
        text.add(line);
        text.add(stateDetail);

        JButton open = new JButton("Open reNgine");
        open.addActionListener(e -> browse(webOrigin() + "/connectors"));
        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
        buttons.add(open);

        JPanel bar = new JPanel(new BorderLayout());
        bar.add(text, BorderLayout.WEST);
        bar.add(buttons, BorderLayout.EAST);
        bar.setBorder(BorderFactory.createEmptyBorder(16, 14, 12, 20));

        JPanel header = new JPanel(new BorderLayout());
        header.add(bar, BorderLayout.CENTER);
        header.add(new JSeparator(), BorderLayout.SOUTH);
        return header;
    }

    private JComponent connection() {
        JPanel form = new JPanel(new GridBagLayout());
        GridBagConstraints c = constraints();
        c.gridy = 0;
        c.gridx = 0;
        form.add(new JLabel("Endpoint"), c);
        c.gridy = 1;
        form.add(new JLabel("Token"), c);
        c.gridx = 1;
        c.weightx = 1;
        c.fill = GridBagConstraints.HORIZONTAL;
        c.insets = new Insets(3, 0, 3, 0);
        c.gridy = 0;
        form.add(endpointField, c);
        c.gridy = 1;
        form.add(tokenField, c);
        c.gridy = 2;
        form.add(allowSelfSigned, c);

        saveAndTest.addActionListener(e -> test());
        allowSelfSigned.addActionListener(e -> save());
        JPanel actionsRow = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        actionsRow.add(saveAndTest);
        actionsRow.add(Box.createHorizontalStrut(10));
        actionsRow.add(status);
        c.gridy = 3;
        form.add(actionsRow, c);
        return section("Connection", form);
    }

    private JComponent workingOn() {
        target.setModel(new DefaultComboBoxModel<>(new Targets.Option[] {Targets.AUTO}));
        target.setPrototypeDisplayValue(
                new Targets.Option("x", "a-fairly-long-target-name.example.com", "target", 100000, 0));
        target.addActionListener(e -> chooseTarget());
        JButton pushScope = new JButton("Apply scope to Burp");
        pushScope.addActionListener(e -> applyScope());
        JButton reload = new JButton("Reload");
        reload.addActionListener(e -> loadTargets());

        JPanel picker = new JPanel(new BorderLayout(6, 0));
        picker.add(target, BorderLayout.CENTER);
        picker.add(reload, BorderLayout.EAST);
        JPanel scope = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        scope.add(pushScope);
        hostLine.setText("No host captured.");

        JPanel body = column(picker, scope, hostLine);
        return section("Working on", body);
    }

    private JComponent captureSection() {
        JPanel tools = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        tools.setBorder(BorderFactory.createEmptyBorder(0, 22, 0, 0));
        tools.add(captureProxy);
        tools.add(Box.createHorizontalStrut(10));
        tools.add(captureRepeater);
        for (JCheckBox box : new JCheckBox[] {
            enabled, captureProxy, captureRepeater, inScopeOnly, captureTitles, sendRequestHead
        }) {
            box.addActionListener(e -> save());
        }
        return section("Capture", column(enabled, tools, inScopeOnly, captureTitles, sendRequestHead));
    }

    private JComponent activity() {
        JPanel tiles = new JPanel(new GridLayout(1, COUNTERS.length, 8, 0));
        for (int i = 0; i < COUNTERS.length; i++) {
            counts[i] = new JLabel("0");
            JLabel caption = new JLabel(COUNTERS[i]);
            JPanel tile = new JPanel();
            tile.setLayout(new BoxLayout(tile, BoxLayout.Y_AXIS));
            tile.setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(new Color(128, 128, 128, 70)),
                    BorderFactory.createEmptyBorder(8, 12, 8, 12)));
            tile.add(counts[i]);
            tile.add(caption);
            tiles.add(tile);
        }
        JPanel body = column(tiles, Box.createVerticalStrut(4), result, received);
        return section("Activity", body);
    }

    private JComponent fromReNgine() {
        JButton openNotice = new JButton("Open in reNgine");
        openNotice.addActionListener(e -> openSelectedNotice());
        JPanel bar = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        bar.add(openNotice);

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
        table.setPreferredSize(new Dimension(400, 220));

        JPanel body = new JPanel(new BorderLayout(0, 8));
        body.add(table, BorderLayout.CENTER);
        body.add(bar, BorderLayout.SOUTH);

        JPanel panel = new JPanel(new BorderLayout(0, 8));
        panel.setBorder(BorderFactory.createEmptyBorder(18, 0, 0, 0));
        panel.add(title("From reNgine"), BorderLayout.NORTH);
        panel.add(body, BorderLayout.CENTER);
        return panel;
    }

    private static GridBagConstraints constraints() {
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(3, 0, 3, 10);
        c.anchor = GridBagConstraints.WEST;
        return c;
    }

    private static JLabel title(String text) {
        JLabel label = new JLabel(text);
        label.setFont(label.getFont().deriveFont(Font.BOLD));
        label.putClientProperty("rengine.title", Boolean.TRUE);
        return label;
    }

    private static JComponent section(String name, JComponent body) {
        JPanel panel = new JPanel(new BorderLayout(0, 8));
        panel.add(title(name), BorderLayout.NORTH);
        panel.add(body, BorderLayout.CENTER);
        panel.setAlignmentX(Component.LEFT_ALIGNMENT);
        return panel;
    }

    private static JPanel column(Component... items) {
        JPanel panel = new JPanel();
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        for (Component item : items) {
            if (item instanceof JComponent component) {
                component.setAlignmentX(Component.LEFT_ALIGNMENT);
            }
            panel.add(item);
            panel.add(Box.createVerticalStrut(4));
        }
        return panel;
    }

    /** Web origin derived from the ingest endpoint. */
    String webOrigin() {
        String value = settings.endpoint().trim();
        int cut = value.indexOf(Settings.INGEST_PATH);
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
        say(url, plain);
    }

    private void say(String text, Color color) {
        status.setText(text);
        status.setForeground(color);
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
            hostLine.setText("Choose a target or a program first.");
            return;
        }
        hostLine.setText("Applying scope.");
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
            SwingUtilities.invokeLater(() -> hostLine.setText(text));
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
            SwingUtilities.invokeLater(() -> hostLine.setText(describe(value)));
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
        if (!settings.endpoint().equals(endpointField.getText())) {
            endpointField.setText(settings.endpoint());
        }
        settings.token(new String(tokenField.getPassword()));
        settings.enabled(enabled.isSelected());
        settings.captureProxy(captureProxy.isSelected());
        settings.captureRepeater(captureRepeater.isSelected());
        settings.inScopeOnly(inScopeOnly.isSelected());
        settings.captureTitles(captureTitles.isSelected());
        settings.sendRequestHead(sendRequestHead.isSelected());
        settings.allowSelfSigned(allowSelfSigned.isSelected());
        settings.save();
        captureProxy.setEnabled(enabled.isSelected());
        captureRepeater.setEnabled(enabled.isSelected());
        say("Saved.", muted);
    }

    private void test() {
        save();
        say("Testing.", muted);
        saveAndTest.setEnabled(false);
        new Thread(() -> {
            String failure = sink.verify();
            SwingUtilities.invokeLater(() -> {
                saveAndTest.setEnabled(true);
                say(failure == null ? "Connected." : failure, failure == null ? OK : FAIL);
                if (failure == null) {
                    loadTargets();
                }
            });
        }, "rengine-connector-test").start();
    }

    private void refresh() {
        long[] values = {
            sink.sent(), sink.queueDepth(), sink.deduped(), sink.dropped(), sink.failed()
        };
        for (int i = 0; i < counts.length; i++) {
            counts[i].setText(String.format("%,d", values[i]));
        }
        counts[3].setForeground(values[3] > 0 ? WARN : plain);
        counts[4].setForeground(values[4] > 0 ? FAIL : plain);
        captureProxy.setEnabled(enabled.isSelected());
        captureRepeater.setEnabled(enabled.isSelected());
        received.setText(describeReceived());
        result.setText(explain());
        renderLink();
        renderNotices();
    }

    /** The header: whether reNgine is answering. */
    private void renderLink() {
        String failure = actions.lastError() != null ? actions.lastError() : sink.lastError();
        if (!settings.isConfigured()) {
            link(muted, "Not configured", "Paste the endpoint and the token from reNgine.");
        } else if (failure != null) {
            link(FAIL, "Not connected", failure);
        } else if (actions.online(ONLINE_MILLIS)) {
            String host = Capture.hostOf(settings.endpoint());
            String detail = (host == null ? "reNgine" : host)
                    + (settings.enabled() ? " · Capture is on" : " · Capture is off");
            link(OK, "Connected", Tls.insecure(settings.endpoint())
                    ? detail + " · Plain HTTP, the token is sent unencrypted" : detail);
        } else {
            link(muted, "Connecting", settings.endpoint());
        }
    }

    private void link(Color color, String title, String detail) {
        dot.setForeground(color);
        state.setText(title);
        stateDetail.setText(detail);
    }

    /** What reNgine handed to Burp. */
    private String describeReceived() {
        String error = actions.lastError();
        if (error != null) {
            return error;
        }
        String summary = handoff.summary();
        return summary.isEmpty() ? "Nothing sent from reNgine." : "From reNgine: " + summary;
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
            return sink.queueDepth() > 0 ? error + " Retrying." : error;
        }
        if (!settings.isConfigured()) {
            return " ";
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
