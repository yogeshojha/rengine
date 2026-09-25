import { mcpApi } from '$lib/api/mcp';
import type {
	McpCall,
	McpSettingsUpdate,
	McpStatus,
	McpToken,
	McpTokenCreate,
	McpTokenCreated,
	McpTokenUpdate,
	McpTool
} from '$lib/types/mcp';
import { toast } from 'svelte-sonner';
import { TRAIL_CAP } from '$lib/utilities/mcp';

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
	let callsLoadedAt = $state<number | null>(null);
	let tokensLoaded = $state(false);

	async function refreshStatus(silent = false) {
		try {
			status = await mcpApi.status();
		} catch (e) {
			if (!silent) toast.error(message(e, 'Server status not loaded'));
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
		get callsLoadedAt() {
			return callsLoadedAt;
		},
		get tokensLoaded() {
			return tokensLoaded;
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
				toast.error(message(e, 'Agents not loaded'));
			} finally {
				isLoading = false;
			}
		},

		refreshStatus,

		async loadTokens(silent = false) {
			try {
				tokens = await mcpApi.tokens();
				tokensLoaded = true;
			} catch (e) {
				if (!silent) toast.error(message(e, 'Agents not loaded'));
			}
		},

		async loadCalls(silent = false) {
			try {
				calls = await mcpApi.calls(TRAIL_CAP);
				callsLoadedAt = Date.now();
			} catch (e) {
				if (!silent) toast.error(message(e, 'Recent calls not loaded'));
			}
		},

		async setRunning(value: boolean): Promise<boolean> {
			isSaving = true;
			try {
				status = await mcpApi.update({ enabled: value });
				toast.success(value ? 'Server started' : 'Server stopped');
				return true;
			} catch (e) {
				toast.error(message(e, 'Server state not changed'));
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
				toast.error(message(e, 'Settings not saved'));
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
				toast.error(message(e, 'Agent not created'));
				return null;
			}
		},

		async updateToken(id: string, body: McpTokenUpdate): Promise<boolean> {
			try {
				const row = await mcpApi.updateToken(id, body);
				tokens = tokens.map((t) => (t.id === id ? row : t));
				toast.success('Access saved');
				return true;
			} catch (e) {
				toast.error(message(e, 'Access not saved'));
				return false;
			}
		},

		async revokeToken(id: string): Promise<boolean> {
			try {
				await mcpApi.revokeToken(id);
				await this.loadTokens();
				await refreshStatus();
				toast.success('Access cut');
				return true;
			} catch (e) {
				toast.error(message(e, 'Access not cut'));
				return false;
			}
		},

		async deleteToken(id: string): Promise<boolean> {
			try {
				await mcpApi.deleteToken(id);
				await this.loadTokens();
				await refreshStatus();
				toast.success('Agent deleted');
				return true;
			} catch (e) {
				toast.error(message(e, 'Agent not deleted'));
				return false;
			}
		},

		async disconnect(tokenId: string): Promise<boolean> {
			try {
				await mcpApi.disconnect(tokenId);
				await refreshStatus();
				return true;
			} catch (e) {
				toast.error(message(e, 'Agent not disconnected'));
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
			callsLoadedAt = null;
			tokensLoaded = false;
		}
	};
}

export const mcp = createMcpStore();
