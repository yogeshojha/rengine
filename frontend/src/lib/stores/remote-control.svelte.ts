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
	ChannelVerifyResult,
	PairingApprove,
	PairingRequest
} from '$lib/types/remote-control';
import { errorMessage } from '$lib/utilities/errors';

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
				toast.error(errorMessage(e, 'Remote control status not loaded'));
			} finally {
				isLoading = false;
			}
		},

		async refreshStatus(silent = false) {
			if (!channel) return;
			try {
				status = await remoteControlApi.status(channel);
			} catch (e) {
				if (!silent) toast.error(errorMessage(e, 'Remote control status not loaded'));
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
				if (!silent) toast.error(errorMessage(e, 'Paired chats not loaded'));
			}
		},

		async loadCalls(silent = false) {
			if (!channel) return;
			try {
				calls = await remoteControlApi.calls(channel);
				callsLoadedAt = Date.now();
			} catch (e) {
				if (!silent) toast.error(errorMessage(e, 'Recent commands not loaded'));
			}
		},

		async save(body: ChannelSettingsUpdate, success?: string): Promise<boolean> {
			if (!channel) return false;
			isSaving = true;
			try {
				apply(await remoteControlApi.update(channel, body));
				if (success) toast.success(success);
				return true;
			} catch (e) {
				toast.error(errorMessage(e, 'Settings not saved'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async setRunning(value: boolean): Promise<boolean> {
			return this.save({ enabled: value }, value ? 'Listener started' : 'Listener stopped');
		},

		async verify(): Promise<ChannelVerifyResult | null> {
			if (!channel) return null;
			try {
				const result = await remoteControlApi.verify(channel);
				await this.refreshStatus(true);
				return result;
			} catch (e) {
				toast.error(errorMessage(e, 'Bot token not verified'));
				return null;
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
				toast.error(errorMessage(e, 'Chat not paired'));
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
				toast.error(errorMessage(e, 'Chat not blocked'));
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
				toast.error(errorMessage(e, 'Chat not updated'));
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
				toast.error(errorMessage(e, 'Chat not revoked'));
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
				toast.error(errorMessage(e, 'Chat not deleted'));
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
