import { toast } from 'svelte-sonner';
import { remoteControlApi } from '$lib/api/remote-control';
import type { ChannelKind } from '$lib/config/channels';
import type {
	ChannelCall,
	ChannelChat,
	ChannelChatUpdate,
	ChannelCommand,
	ChannelSettingsUpdate,
	ChannelStatus,
	PairingApprove,
	PairingRequest
} from '$lib/types/remote-control';

function message(e: unknown, fallback: string): string {
	return e instanceof Error ? e.message : fallback;
}

function createRemoteControlStore() {
	let channel = $state<ChannelKind | null>(null);
	let status = $state<ChannelStatus | null>(null);
	let pending = $state<PairingRequest[]>([]);
	let chats = $state<ChannelChat[]>([]);
	let commands = $state<ChannelCommand[]>([]);
	let calls = $state<ChannelCall[]>([]);
	let isLoading = $state(false);
	let isSaving = $state(false);
	let callsLoadedAt = $state<number | null>(null);

	function apply(next: ChannelStatus) {
		status = next;
	}

	return {
		get channel() {
			return channel;
		},
		get status() {
			return status;
		},
		get pending() {
			return pending;
		},
		get chats() {
			return chats;
		},
		get commands() {
			return commands;
		},
		get calls() {
			return calls;
		},
		get isLoading() {
			return isLoading;
		},
		get isSaving() {
			return isSaving;
		},
		get callsLoadedAt() {
			return callsLoadedAt;
		},

		async fetch(kind: ChannelKind, force = false) {
			if (isLoading || (channel === kind && status && !force)) return;
			isLoading = true;
			try {
				const [s, c] = await Promise.all([
					remoteControlApi.status(kind),
					remoteControlApi.commands(kind)
				]);
				channel = kind;
				status = s;
				commands = c;
			} catch (e) {
				toast.error(message(e, 'Remote control status not loaded'));
			} finally {
				isLoading = false;
			}
		},

		async refreshStatus(silent = false) {
			if (!channel) return;
			try {
				status = await remoteControlApi.status(channel);
			} catch (e) {
				if (!silent) toast.error(message(e, 'Remote control status not loaded'));
			}
		},

		async loadAdmin(silent = false) {
			if (!channel) return;
			try {
				const [p, c] = await Promise.all([
					remoteControlApi.pending(channel),
					remoteControlApi.chats(channel)
				]);
				pending = p;
				chats = c;
			} catch (e) {
				if (!silent) toast.error(message(e, 'Paired chats not loaded'));
			}
		},

		async loadCalls(silent = false) {
			if (!channel) return;
			try {
				calls = await remoteControlApi.calls(channel);
				callsLoadedAt = Date.now();
			} catch (e) {
				if (!silent) toast.error(message(e, 'Recent commands not loaded'));
			}
		},

		async save(body: ChannelSettingsUpdate, success?: string): Promise<boolean> {
			if (!channel) return false;
			isSaving = true;
			try {
				apply(await remoteControlApi.update(channel, body));
				if (body.ceiling) void this.loadAdmin(true);
				if (success) toast.success(success);
				return true;
			} catch (e) {
				toast.error(message(e, 'Settings not saved'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async setRunning(value: boolean): Promise<boolean> {
			return this.save({ enabled: value }, value ? 'Listener started' : 'Listener stopped');
		},

		async connect(token: string): Promise<string | null> {
			if (!channel) return null;
			isSaving = true;
			try {
				status = await remoteControlApi.connect(channel, token);
				await this.loadAdmin(true);
				toast.success(`@${status.bot?.username ?? 'bot'} connected`);
				return null;
			} catch (e) {
				return message(e, 'Bot not connected');
			} finally {
				isSaving = false;
			}
		},

		async disconnect(): Promise<boolean> {
			if (!channel) return false;
			isSaving = true;
			try {
				status = await remoteControlApi.disconnect(channel);
				pending = [];
				chats = [];
				toast.success('Bot disconnected');
				return true;
			} catch (e) {
				toast.error(message(e, 'Bot not disconnected'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async approve(code: string, body: PairingApprove): Promise<ChannelChat | null> {
			if (!channel) return null;
			try {
				const chat = await remoteControlApi.approve(channel, code, body);
				toast.success('Chat paired');
				await Promise.all([this.loadAdmin(true), this.refreshStatus(true)]);
				return chat;
			} catch (e) {
				toast.error(message(e, 'Chat not paired'));
				return null;
			}
		},

		async block(code: string): Promise<boolean> {
			if (!channel) return false;
			try {
				await remoteControlApi.block(channel, code);
				toast.success('Chat blocked');
				await Promise.all([this.loadAdmin(true), this.refreshStatus(true)]);
				return true;
			} catch (e) {
				toast.error(message(e, 'Chat not blocked'));
				return false;
			}
		},

		async updateChat(id: string, body: ChannelChatUpdate): Promise<boolean> {
			if (!channel) return false;
			try {
				const updated = await remoteControlApi.updateChat(channel, id, body);
				chats = chats.map((c) => (c.id === id ? updated : c));
				toast.success('Chat updated');
				return true;
			} catch (e) {
				toast.error(message(e, 'Chat not updated'));
				return false;
			}
		},

		async revokeChat(id: string): Promise<boolean> {
			if (!channel) return false;
			try {
				const updated = await remoteControlApi.revokeChat(channel, id);
				chats = chats.map((c) => (c.id === id ? updated : c));
				toast.success('Chat revoked');
				await this.refreshStatus(true);
				return true;
			} catch (e) {
				toast.error(message(e, 'Chat not revoked'));
				return false;
			}
		},

		async deleteChat(id: string): Promise<boolean> {
			if (!channel) return false;
			try {
				await remoteControlApi.deleteChat(channel, id);
				chats = chats.filter((c) => c.id !== id);
				toast.success('Chat deleted');
				await this.refreshStatus(true);
				return true;
			} catch (e) {
				toast.error(message(e, 'Chat not deleted'));
				return false;
			}
		},

		reset() {
			channel = null;
			status = null;
			pending = [];
			chats = [];
			commands = [];
			calls = [];
			isLoading = false;
			isSaving = false;
			callsLoadedAt = null;
		}
	};
}

export const remoteControl = createRemoteControlStore();
