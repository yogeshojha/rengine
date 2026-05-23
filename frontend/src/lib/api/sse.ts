import { SESSION_EXPIRED_EVENT } from './client';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface SSEMessage {
    /** Channel this event was published to */
    channel: string;
    /** Event type within the channel (e.g. 'activity', 'notification', 'scan_progress') */
    type: string;
    /** Event payload — shape depends on type */
    data: Record<string, unknown>;
    /** ISO timestamp from the server */
    ts: string;
}

type MessageCallback = (message: SSEMessage) => void;
type StateCallback = (state: ConnectionState) => void;

/**
 * After this many consecutive failures we attempt a silent token refresh
 * before continuing the reconnect loop.  EventSource doesn't expose HTTP
 * status codes so we can't distinguish 401 from a transient network error —
 * a proactive refresh after a few failures handles both cases gracefully.
 */
const REFRESH_ATTEMPT_AFTER_FAILURES = 3;

export class SSEClient {
    private eventSource: EventSource | null = null;
    private channels: Set<string> = new Set();

    private subscriptions: Map<string, Set<MessageCallback>> = new Map();

    private stateListeners: Set<StateCallback> = new Set();

    private _state: ConnectionState = 'disconnected';
    private reconnectAttempts = 0;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    private readonly maxReconnectAttempts = 10;
    private readonly baseDelay = 1000;     // 1s
    private readonly maxDelay = 30_000;    // 30s

    /**
     * Opens an SSE connection subscribed to the given channels.
     *
     * If already connected, the connection is recycled only if the
     * channel set has changed.
     */
    connect(channels: string[]): void {
        const incoming = new Set(channels);
        const changed = !this.setsEqual(this.channels, incoming);

        if (this.eventSource && !changed) {
            return;
        }

        this.channels = incoming;
        this.reconnectAttempts = 0;
        this.openConnection();
    }

    /**
     * Add channels to an existing connection.
     * Triggers a reconnect with the updated channel set.
     */
    addChannels(channels: string[]): void {
        let changed = false;
        for (const ch of channels) {
            if (!this.channels.has(ch)) {
                this.channels.add(ch);
                changed = true;
            }
        }
        if (changed && this._state !== 'disconnected') {
            this.openConnection();
        }
    }

    /**
     * Remove channels from the connection.
     * Triggers a reconnect with the reduced channel set.
     */
    removeChannels(channels: string[]): void {
        let changed = false;
        for (const ch of channels) {
            if (this.channels.delete(ch)) {
                changed = true;
                this.subscriptions.delete(ch);
            }
        }
        if (changed && this._state !== 'disconnected') {
            if (this.channels.size === 0) {
                this.disconnect();
            } else {
                this.openConnection();
            }
        }
    }

    /**
     * Subscribe to events on a specific channel.
     * Returns an unsubscribe function for cleanup.
     */
    subscribe(channel: string, callback: MessageCallback): () => void {
        if (!this.subscriptions.has(channel)) {
            this.subscriptions.set(channel, new Set());
        }
        this.subscriptions.get(channel)!.add(callback);

        return () => {
            const subs = this.subscriptions.get(channel);
            if (subs) {
                subs.delete(callback);
                if (subs.size === 0) {
                    this.subscriptions.delete(channel);
                }
            }
        };
    }

    /**
     * Subscribe to connection state changes.
     * Returns an unsubscribe function.
     */
    onStateChange(callback: StateCallback): () => void {
        this.stateListeners.add(callback);
        callback(this._state);

        return () => {
            this.stateListeners.delete(callback);
        };
    }

    /** Cleanly close the connection and stop reconnecting. */
    disconnect(): void {
        this.clearReconnectTimer();
        this.closeEventSource();
        this.channels.clear();
        this.setState('disconnected');
    }

    /** Current connection state. */
    get state(): ConnectionState {
        return this._state;
    }

    /** Whether the connection is open and receiving. */
    get isConnected(): boolean {
        return this._state === 'connected';
    }

    /** Channels currently subscribed to on the server. */
    get activeChannels(): ReadonlySet<string> {
        return this.channels;
    }

    private openConnection(): void {
        this.closeEventSource();
        this.clearReconnectTimer();

        if (this.channels.size === 0) {
            this.setState('disconnected');
            return;
        }

        const channelParam = encodeURIComponent(
            Array.from(this.channels).join(',')
        );
        const url = `/api/v1/events/stream?channels=${channelParam}`;

        this.setState(
            this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting'
        );

        // withCredentials ensures cookies (auth tokens) are sent for both
        // same-origin and any future cross-origin deployments.
        const es = new EventSource(url, { withCredentials: true });

        es.addEventListener('message', (event: MessageEvent) => {
            this.handleMessage(event);
        });

        es.onopen = () => {
            this.reconnectAttempts = 0;
            this.setState('connected');
            console.log(
                `[SSE] Connected — channels: ${Array.from(this.channels).join(', ')}`
            );
        };

        es.onerror = () => {
            this.handleError();
        };

        this.eventSource = es;
    }

    private handleMessage(event: MessageEvent): void {
        let message: SSEMessage;
        try {
            message = JSON.parse(event.data) as SSEMessage;
        } catch {
            console.error('[SSE] Failed to parse message:', event.data);
            return;
        }

        // Route to channel subscribers
        const subs = this.subscriptions.get(message.channel);
        if (subs) {
            for (const cb of subs) {
                try {
                    cb(message);
                } catch (err) {
                    console.error('[SSE] Subscriber error:', err);
                }
            }
        }

        // Also route broadcast events to all subscribers
        if (message.channel === 'broadcast') {
            for (const [channel, channelSubs] of this.subscriptions) {
                if (channel === 'broadcast') continue;
                for (const cb of channelSubs) {
                    try {
                        cb(message);
                    } catch (err) {
                        console.error('[SSE] Subscriber error:', err);
                    }
                }
            }
        }
    }

    private handleError(): void {
        this.closeEventSource();

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(
                `[SSE] Giving up after ${this.maxReconnectAttempts} attempts`
            );
            this.setState('disconnected');
            return;
        }

        // After a few consecutive failures attempt a silent token refresh.
        // EventSource doesn't expose the HTTP status, so we can't tell a 401
        // from a network blip — proactive refresh handles both.
        if (this.reconnectAttempts === REFRESH_ATTEMPT_AFTER_FAILURES) {
            this.refreshAndReconnect();
            return;
        }

        this.scheduleReconnect();
    }

    private async refreshAndReconnect(): Promise<void> {
        try {
            const response = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                credentials: 'include',
            });

            if (!response.ok) {
                console.error('[SSE] Token refresh failed — session expired');
                window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
                this.setState('disconnected');
                return;
            }

            // Refresh succeeded — reset counter so the reconnect gets full retries
            this.reconnectAttempts = 0;
        } catch {
            // Network error during refresh — try reconnecting anyway
        }

        this.scheduleReconnect();
    }

    private scheduleReconnect(): void {
        const exponential = this.baseDelay * Math.pow(2, this.reconnectAttempts);
        const capped = Math.min(exponential, this.maxDelay);
        const jitter = capped * 0.2 * Math.random();
        const delay = capped + jitter;

        this.reconnectAttempts++;
        this.setState('reconnecting');

        console.log(
            `[SSE] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
        );

        this.reconnectTimer = setTimeout(() => {
            this.openConnection();
        }, delay);
    }

    private closeEventSource(): void {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    private clearReconnectTimer(): void {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    private setState(state: ConnectionState): void {
        if (this._state === state) return;
        this._state = state;
        for (const cb of this.stateListeners) {
            try {
                cb(state);
            } catch (err) {
                console.error('[SSE] State listener error:', err);
            }
        }
    }

    private setsEqual<T>(a: Set<T>, b: Set<T>): boolean {
        if (a.size !== b.size) return false;
        for (const item of a) {
            if (!b.has(item)) return false;
        }
        return true;
    }
}

export const sseClient = new SSEClient();
