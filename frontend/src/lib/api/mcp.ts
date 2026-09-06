import { api } from './client';
import type {
	McpCall,
	McpSettingsUpdate,
	McpStatus,
	McpToken,
	McpTokenCreate,
	McpTokenCreated,
	McpTool
} from '$lib/types/mcp';

export const mcpApi = {
	status(): Promise<McpStatus> {
		return api.get<McpStatus>('/mcp/status');
	},

	update(body: McpSettingsUpdate): Promise<McpStatus> {
		return api.patch<McpStatus>('/mcp/settings', body);
	},

	tools(): Promise<McpTool[]> {
		return api.get<McpTool[]>('/mcp/tools');
	},

	calls(limit = 100): Promise<McpCall[]> {
		return api.get<McpCall[]>(`/mcp/calls?limit=${limit}`);
	},

	tokens(): Promise<McpToken[]> {
		return api.get<McpToken[]>('/mcp/tokens');
	},

	createToken(body: McpTokenCreate): Promise<McpTokenCreated> {
		return api.post<McpTokenCreated>('/mcp/tokens', body);
	},

	revokeToken(id: string): Promise<void> {
		return api.post<void>(`/mcp/tokens/${id}/revoke`);
	},

	deleteToken(id: string): Promise<void> {
		return api.delete<void>(`/mcp/tokens/${id}`);
	},

	disconnect(tokenId: string): Promise<{ dropped: number }> {
		return api.post<{ dropped: number }>(`/mcp/sessions/${tokenId}/disconnect`);
	}
};
