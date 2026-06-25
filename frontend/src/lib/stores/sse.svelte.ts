import { sseClient, type ConnectionState, type SSEMessage } from '$lib/api/sse';
import { SSEChannel } from '$lib/types/sse';

interface SSEStoreState {
	connectionState: ConnectionState;
	activeChannels: string[];
}

const state = $state<SSEStoreState>({
	connectionState: 'disconnected',
	activeChannels: []
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

	get activeChannels(): string[] {
		return state.activeChannels;
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
			state.activeChannels = Array.from(sseClient.activeChannels);
		});

		sseClient.connect(channels);
	},

	switchProject(oldProjectId: string | undefined, newProjectId: string): void {
		if (oldProjectId) {
			sseClient.removeChannels([SSEChannel.project(oldProjectId)]);
		}
		sseClient.addChannels([SSEChannel.project(newProjectId)]);
		state.activeChannels = Array.from(sseClient.activeChannels);
	},

	subscribe(channel: string, callback: (message: SSEMessage) => void): () => void {
		return sseClient.subscribe(channel, callback);
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

	destroy(): void {
		stateUnsub?.();
		stateUnsub = null;
		sseClient.disconnect();
		state.connectionState = 'disconnected';
		state.activeChannels = [];
	}
};
