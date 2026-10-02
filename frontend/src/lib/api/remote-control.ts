import { api } from './client';
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

const base = (channel: ChannelKind) => `/remote-control/channels/${channel}`;

export const remoteControlApi = {
	status(channel: ChannelKind): Promise<ChannelStatus> {
		return api.get<ChannelStatus>(`${base(channel)}/status`);
	},

	update(channel: ChannelKind, body: ChannelSettingsUpdate): Promise<ChannelStatus> {
		return api.patch<ChannelStatus>(`${base(channel)}/settings`, body);
	},

	connect(channel: ChannelKind, token: string): Promise<ChannelStatus> {
		return api.post<ChannelStatus>(`${base(channel)}/connect`, { token });
	},

	disconnect(channel: ChannelKind): Promise<ChannelStatus> {
		return api.post<ChannelStatus>(`${base(channel)}/disconnect`);
	},

	pending(channel: ChannelKind): Promise<PairingRequest[]> {
		return api.get<PairingRequest[]>(`${base(channel)}/pending`);
	},

	approve(channel: ChannelKind, code: string, body: PairingApprove): Promise<ChannelChat> {
		return api.post<ChannelChat>(
			`${base(channel)}/pending/${encodeURIComponent(code)}/approve`,
			body
		);
	},

	block(channel: ChannelKind, code: string): Promise<void> {
		return api.post<void>(`${base(channel)}/pending/${encodeURIComponent(code)}/block`);
	},

	chats(channel: ChannelKind): Promise<ChannelChat[]> {
		return api.get<ChannelChat[]>(`${base(channel)}/chats`);
	},

	updateChat(channel: ChannelKind, id: string, body: ChannelChatUpdate): Promise<ChannelChat> {
		return api.patch<ChannelChat>(`${base(channel)}/chats/${id}`, body);
	},

	revokeChat(channel: ChannelKind, id: string): Promise<ChannelChat> {
		return api.post<ChannelChat>(`${base(channel)}/chats/${id}/revoke`);
	},

	deleteChat(channel: ChannelKind, id: string): Promise<void> {
		return api.delete<void>(`${base(channel)}/chats/${id}`);
	},

	commands(channel: ChannelKind): Promise<ChannelCommand[]> {
		return api.get<ChannelCommand[]>(`${base(channel)}/commands`);
	},

	calls(channel: ChannelKind, limit = 200): Promise<ChannelCall[]> {
		return api.get<ChannelCall[]>(`${base(channel)}/calls?limit=${limit}`);
	}
};
