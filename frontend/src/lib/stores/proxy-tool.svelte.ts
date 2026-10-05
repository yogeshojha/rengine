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

function storedAsk(): boolean {
	try {
		return localStorage.getItem(STORAGE_KEYS.proxyConfirm) !== 'off';
	} catch {
		return true;
	}
}

interface Confirmation {
	title: string;
	note: string | null;
	resolve: (ok: boolean) => void;
}

function createProxyTool() {
	let kind = $state<ActionKind>(
		typeof localStorage === 'undefined' ? DEFAULT_ACTION_KIND : stored()
	);
	let ask = $state(typeof localStorage === 'undefined' ? true : storedAsk());
	let pending = $state.raw<Confirmation | null>(null);

	function setAsk(next: boolean) {
		ask = next;
		try {
			if (next) localStorage.removeItem(STORAGE_KEYS.proxyConfirm);
			else localStorage.setItem(STORAGE_KEYS.proxyConfirm, 'off');
		} catch {
			return;
		}
	}

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
		},
		get ask() {
			return ask;
		},
		setAsk,
		get pending() {
			return pending;
		},
		/** Resolves true once the send is confirmed, at once when confirmation is off. */
		confirm(title: string, note: string | null = null): Promise<boolean> {
			if (!ask) return Promise.resolve(true);
			pending?.resolve(false);
			return new Promise((resolve) => {
				pending = { title, note, resolve };
			});
		},
		settle(ok: boolean, skipNext = false) {
			const open = pending;
			if (!open) return;
			pending = null;
			if (ok && skipNext) setAsk(false);
			open.resolve(ok);
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
