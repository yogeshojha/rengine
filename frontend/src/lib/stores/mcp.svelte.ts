import { mcpApi } from '$lib/api/mcp';
import type {
	McpCall,
	McpSettingsUpdate,
	McpStatus,
	McpToken,
	McpTokenCreate,
	McpTokenCreated,
	McpTool
} from '$lib/types/mcp';
import { toast } from 'svelte-sonner';

function message(e: unknown, fallback: string): string {
	return e instanceof Error ? e.message : fallback;
}

function createMcpStore() {
	let status = $state<McpStatus | null>(null);
	let tools = $state<McpTool[]>([]);
	let tokens = $state<McpToken[]>([]);
	let calls = $state<McpCall[]>([]);
	let isLoading = $state(false);
	let isSaving = $state(false);
	let hasFetched = $state(false);

	async function refreshStatus() {
		try {
			status = await mcpApi.status();
		} catch (e) {
			toast.error(message(e, 'MCP server status could not be loaded'));
		}
	}

	return {
		get status() {
			return status;
		},
		get tools() {
			return tools;
		},
		get tokens() {
			return tokens;
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
		get hasFetched() {
			return hasFetched;
		},
		get running() {
			return status?.enabled ?? false;
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				const [s, t] = await Promise.all([mcpApi.status(), mcpApi.tools()]);
				status = s;
				tools = t;
				hasFetched = true;
			} catch (e) {
				toast.error(message(e, 'MCP page could not be loaded'));
			} finally {
				isLoading = false;
			}
		},

		refreshStatus,

		async loadTokens() {
			try {
				tokens = await mcpApi.tokens();
			} catch (e) {
				toast.error(message(e, 'Service tokens could not be loaded'));
			}
		},

		async loadCalls() {
			try {
				calls = await mcpApi.calls();
			} catch (e) {
				toast.error(message(e, 'Recent calls could not be loaded'));
			}
		},

		async setRunning(value: boolean): Promise<boolean> {
			isSaving = true;
			try {
				status = await mcpApi.update({ enabled: value });
				toast.success(value ? 'MCP server started.' : 'MCP server stopped.');
				return true;
			} catch (e) {
				toast.error(message(e, 'Server state could not be changed'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async save(body: McpSettingsUpdate): Promise<boolean> {
			isSaving = true;
			try {
				status = await mcpApi.update(body);
				return true;
			} catch (e) {
				toast.error(message(e, 'MCP settings could not be saved'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async createToken(body: McpTokenCreate): Promise<McpTokenCreated | null> {
			try {
				const created = await mcpApi.createToken(body);
				await this.loadTokens();
				await refreshStatus();
				return created;
			} catch (e) {
				toast.error(message(e, 'Token could not be created'));
				return null;
			}
		},

		async revokeToken(id: string): Promise<boolean> {
			try {
				await mcpApi.revokeToken(id);
				await this.loadTokens();
				await refreshStatus();
				toast.success('Token revoked.');
				return true;
			} catch (e) {
				toast.error(message(e, 'Token could not be revoked'));
				return false;
			}
		},

		async deleteToken(id: string): Promise<boolean> {
			try {
				await mcpApi.deleteToken(id);
				await this.loadTokens();
				await refreshStatus();
				toast.success('Token deleted.');
				return true;
			} catch (e) {
				toast.error(message(e, 'Token could not be deleted'));
				return false;
			}
		},

		async disconnect(tokenId: string): Promise<boolean> {
			try {
				await mcpApi.disconnect(tokenId);
				await refreshStatus();
				return true;
			} catch (e) {
				toast.error(message(e, 'Agent could not be disconnected'));
				return false;
			}
		},

		reset() {
			status = null;
			tools = [];
			tokens = [];
			calls = [];
			isLoading = false;
			isSaving = false;
			hasFetched = false;
		}
	};
}

export const mcp = createMcpStore();
