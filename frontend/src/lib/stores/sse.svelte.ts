import { sseClient, type ConnectionState } from '$lib/api/sse';
import { SSEChannel } from '$lib/types/sse';

interface SSEStoreState {
	connectionState: ConnectionState;
}

const state = $state<SSEStoreState>({
	connectionState: 'disconnected'
});

let stateUnsub: (() => void) | null = null;

export const sseStore = {
	get connectionState(): ConnectionState {
		return state.connectionState;
	},

	get isConnected(): boolean {
		return state.connectionState === 'connected';
	},

	get isReconnecting(): boolean {
		return state.connectionState === 'reconnecting';
	},

	init(projectId?: string): void {
		stateUnsub?.();
		stateUnsub = null;

		const channels: string[] = [SSEChannel.BROADCAST];

		if (projectId) {
			channels.push(SSEChannel.project(projectId));
		}

		stateUnsub = sseClient.onStateChange((newState) => {
			state.connectionState = newState;
		});

		sseClient.connect(channels);
	},

	on<T = Record<string, unknown>>(
		channel: string,
		eventType: string,
		callback: (data: T) => void
	): () => void {
		return sseClient.subscribe(channel, (message) => {
			if (message.type === eventType) {
				callback(message.data as T);
			}
		});
	},

	onResume(callback: () => void): () => void {
		return sseClient.onResume(callback);
	},

	destroy(): void {
		stateUnsub?.();
		stateUnsub = null;
		sseClient.disconnect();
		state.connectionState = 'disconnected';
	}
};
