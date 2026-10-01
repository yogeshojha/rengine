import { ActionKind, DEFAULT_ACTION_KIND, HANDOFF_KINDS } from '$lib/config/connectors';
import { STORAGE_KEYS } from '$lib/config/storage-keys';

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
