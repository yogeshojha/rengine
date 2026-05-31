/**
 * Provides reactive state ($state) for connection status and
 * helper methods for component-level subscriptions.
 *
 * Usage in a layout/root component we only initialize once:
 *
 *   import { sseStore } from '$lib/stores/sse.svelte';
 *
 *   $effect(() => {
 *       sseStore.init(projectId);
 *       return () => sseStore.destroy();
 *   });
 *
 * Usage in any component:
 *
 *   import { sseStore } from '$lib/stores/sse.svelte';
 *
 *   // Reactive connection state
 *   {#if sseStore.isConnected}
 *       <span class="text-green-500">● Live</span>
 *   {/if}
 *
 *   // Subscribe to channel events
 *   $effect(() => {
 *       const unsub = sseStore.subscribe('project:abc', (msg) => {
 *           if (msg.type === 'activity') { ... }
 *       });
 *       return unsub;
 *   });
 */

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

	/**
	 * Initialize the SSE connection.
	 * Always subscribes to `broadcast` (system-wide notifications).
	 * Optionally subscribes to a project channel for scoped events.
	 */
	init(projectId?: string): void {
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

	/**
	 * Switch project context (e.g. user navigates to a different project).
	 * Swaps the project channel without tearing down the entire connection.
	 */
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

	/**
	 * Subscribe and filter by event type within a channel.
	 * Convenience wrapper for the common pattern.
	 *
	 * Example:
	 *   sseStore.on<Notification>(SSEChannel.BROADCAST, SSEEventType.NOTIFICATION, (data) => {
	 *       // data is typed as Notification
	 *   });
	 */
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
