import { api, API_PREFIX } from './client';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface SSEMessage {
	channel: string;
	type: string;
	data: Record<string, unknown>;
	ts: string;
}

type MessageCallback = (message: SSEMessage) => void;
type StateCallback = (state: ConnectionState) => void;

const REFRESH_ATTEMPT_AFTER_FAILURES = 3;
const MAX_REFRESHES = 3;
const HIDDEN_PAUSE_MS = 30_000;

class SSEClient {
	private eventSource: EventSource | null = null;
	private channels: Set<string> = new Set();

	private subscriptions: Map<string, Set<MessageCallback>> = new Map();

	private stateListeners: Set<StateCallback> = new Set();
	private resumeListeners: Set<() => void> = new Set();

	private paused = false;
	private resyncPending = false;
	private hiddenTimer: ReturnType<typeof setTimeout> | null = null;

	private _state: ConnectionState = 'disconnected';
	private reconnectAttempts = 0;
	private refreshAttempts = 0;
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

	private readonly maxReconnectAttempts = 10;
	private readonly baseDelay = 1000; // 1s
	private readonly maxDelay = 30_000; // 30s

	constructor() {
		if (typeof window === 'undefined') return;
		window.addEventListener('pagehide', () => this.pause());
		window.addEventListener('pageshow', (e) => {
			if (e.persisted) this.resume();
		});
		document.addEventListener('visibilitychange', () => {
			if (this.hiddenTimer) clearTimeout(this.hiddenTimer);
			this.hiddenTimer = null;
			if (document.visibilityState === 'hidden') {
				this.hiddenTimer = setTimeout(() => this.pause(), HIDDEN_PAUSE_MS);
			} else {
				this.resume();
			}
		});
	}

	connect(channels: string[]): void {
		const incoming = new Set(channels);
		const changed = !this.setsEqual(this.channels, incoming);

		if (this.eventSource && !changed) {
			return;
		}

		this.channels = incoming;
		this.paused = false;
		this.reconnectAttempts = 0;
		this.refreshAttempts = 0;
		this.openConnection();
	}

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

	onStateChange(callback: StateCallback): () => void {
		this.stateListeners.add(callback);
		callback(this._state);

		return () => {
			this.stateListeners.delete(callback);
		};
	}

	onResume(callback: () => void): () => void {
		this.resumeListeners.add(callback);
		return () => {
			this.resumeListeners.delete(callback);
		};
	}

	disconnect(): void {
		this.paused = false;
		this.resyncPending = false;
		this.clearReconnectTimer();
		this.closeEventSource();
		this.channels.clear();
		this.setState('disconnected');
	}

	private pause(): void {
		if (this.paused || (!this.eventSource && !this.reconnectTimer)) return;
		this.paused = true;
		this.clearReconnectTimer();
		this.closeEventSource();
		this.setState('disconnected');
	}

	private resume(): void {
		if (!this.paused) return;
		this.paused = false;
		if (this.channels.size === 0) return;
		this.reconnectAttempts = 0;
		this.refreshAttempts = 0;
		this.resyncPending = true;
		this.openConnection();
	}

	private openConnection(): void {
		this.closeEventSource();
		this.clearReconnectTimer();

		if (this.channels.size === 0) {
			this.setState('disconnected');
			return;
		}

		const channelParam = encodeURIComponent(Array.from(this.channels).join(','));
		const url = `${API_PREFIX}/events/stream?channels=${channelParam}`;

		this.setState(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');

		const es = new EventSource(url, { withCredentials: true });

		es.addEventListener('message', (event: MessageEvent) => {
			this.handleMessage(event);
		});

		es.addEventListener('unauthorized', () => {
			this.closeEventSource();
			void this.refreshAndReconnect();
		});

		es.onopen = () => {
			this.reconnectAttempts = 0;
			this.refreshAttempts = 0;
			this.setState('connected');
			if (this.resyncPending) {
				this.resyncPending = false;
				for (const cb of this.resumeListeners) {
					try {
						cb();
					} catch (err) {
						console.error('[SSE] Resume listener error:', err);
					}
				}
			}
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
		this.resyncPending = true;

		if (this.reconnectAttempts >= this.maxReconnectAttempts) {
			console.error(`[SSE] Giving up after ${this.maxReconnectAttempts} attempts`);
			this.setState('disconnected');
			return;
		}

		if (
			this.reconnectAttempts === REFRESH_ATTEMPT_AFTER_FAILURES &&
			this.refreshAttempts < MAX_REFRESHES
		) {
			void this.refreshAndReconnect();
			return;
		}

		this.scheduleReconnect();
	}

	private async refreshAndReconnect(): Promise<void> {
		this.refreshAttempts++;
		const result = await api.refreshSession();
		if (result === 'expired') {
			this.setState('disconnected');
			return;
		}
		if (result === 'ok' && this.refreshAttempts < MAX_REFRESHES) this.reconnectAttempts = 0;
		this.scheduleReconnect();
	}

	private scheduleReconnect(): void {
		if (this.paused) return;
		const exponential = this.baseDelay * Math.pow(2, this.reconnectAttempts);
		const capped = Math.min(exponential, this.maxDelay);
		const jitter = capped * 0.2 * Math.random();
		const delay = capped + jitter;

		this.reconnectAttempts++;
		this.setState('reconnecting');

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
