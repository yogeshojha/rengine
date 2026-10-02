import {
	ActionKind,
	CONNECTOR_POLL_MS,
	DEFAULT_ACTION_KIND,
	HANDOFF_KINDS
} from '$lib/config/connectors';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { connectors } from '$lib/stores/connectors.svelte';

function stored(): ActionKind {
	try {
		const value = localStorage.getItem(STORAGE_KEYS.proxyLastTool) as ActionKind | null;
		return value && HANDOFF_KINDS.includes(value) ? value : DEFAULT_ACTION_KIND;
	} catch {
		return DEFAULT_ACTION_KIND;
	}
}

function createProxyTool() {
	let kind = $state<ActionKind>(
		typeof localStorage === 'undefined' ? DEFAULT_ACTION_KIND : stored()
	);

	return {
		get kind() {
			return kind;
		},
		set(next: ActionKind) {
			kind = next;
			try {
				localStorage.setItem(STORAGE_KEYS.proxyLastTool, next);
			} catch {
				return;
			}
		}
	};
}

export const proxyTool = createProxyTool();

let pollers = 0;
let watched: string | null = null;
let refreshedAt = 0;
let timer: ReturnType<typeof setInterval> | undefined;

function refresh(projectId: string) {
	if (document.hidden) return;
	refreshedAt = Date.now();
	void connectors.load(projectId, connectors.fetchedProjectId === projectId);
	void connectors.loadCatalog();
}

function loadedWithin(projectId: string, ms: number): boolean {
	const at = Math.max(refreshedAt, connectors.loadedAt);
	return connectors.fetchedProjectId === projectId && Date.now() - at < ms;
}

/** Reloads the connection state when it is older than one poll. */
export function freshenProxyPresence(projectId: string) {
	if (!loadedWithin(projectId, CONNECTOR_POLL_MS)) refresh(projectId);
}

/** Keeps the connection state current while a visible send control is mounted. */
export function watchProxyPresence(projectId: string): () => void {
	freshenProxyPresence(projectId);
	pollers++;
	watched = projectId;
	timer ??= setInterval(() => {
		if (watched && !loadedWithin(watched, CONNECTOR_POLL_MS / 2)) refresh(watched);
	}, CONNECTOR_POLL_MS);
	return () => {
		pollers--;
		if (pollers > 0) return;
		clearInterval(timer);
		timer = undefined;
	};
}
