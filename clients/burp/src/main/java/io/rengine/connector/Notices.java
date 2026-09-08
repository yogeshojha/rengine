package io.rengine.connector;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/** The last few things reNgine said, newest first. Bounded: a session is long. */
final class Notices {
    static final int KEEP = 12;

    private final Deque<Actions.Notice> recent = new ArrayDeque<>();

    synchronized void add(Actions.Notice notice) {
        recent.addFirst(notice);
        while (recent.size() > KEEP) {
            recent.removeLast();
        }
    }

    synchronized List<Actions.Notice> recent() {
        return new ArrayList<>(recent);
    }

    synchronized int size() {
        return recent.size();
    }
}
