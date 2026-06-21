import { instanceSettingsApi } from '$lib/api/instanceSettings';
import {
	capabilitiesForMode,
	coerceInstanceMode,
	DEFAULT_INSTANCE_MODE,
	type CapabilityKey
} from '$lib/config/capabilities';

function createCapabilitiesStore() {
	let mode = $state<string>(DEFAULT_INSTANCE_MODE);
	let capabilities = $state<string[]>(capabilitiesForMode(DEFAULT_INSTANCE_MODE));
	let hasFetched = $state(false);
	let loading = false;

	return {
		get mode() {
			return mode;
		},
		get capabilities() {
			return capabilities;
		},
		get hasFetched() {
			return hasFetched;
		},
		has(capability: CapabilityKey): boolean {
			return capabilities.includes(capability);
		},
		setMode(next: string) {
			mode = next;
			capabilities = capabilitiesForMode(next);
		},
		async fetch() {
			if (loading) return;
			loading = true;
			try {
				const s = await instanceSettingsApi.get();
				mode = coerceInstanceMode(s.mode);
				capabilities = s.capabilities ?? capabilitiesForMode(s.mode);
				hasFetched = true;
			} catch {
			} finally {
				loading = false;
			}
		},
		reset() {
			mode = DEFAULT_INSTANCE_MODE;
			capabilities = capabilitiesForMode(DEFAULT_INSTANCE_MODE);
			hasFetched = false;
		}
	};
}

export const capabilitiesStore = createCapabilitiesStore();
