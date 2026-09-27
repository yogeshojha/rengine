import { instanceSettingsApi } from '$lib/api/instanceSettings';
import {
	capabilitiesForMode,
	coerceInstanceMode,
	DEFAULT_INSTANCE_MODE,
	type CapabilityKey
} from '$lib/config/capabilities';
import { PRODUCT_NAME } from '$lib/constants';

function createCapabilitiesStore() {
	let mode = $state<string>(DEFAULT_INSTANCE_MODE);
	let capabilities = $state<string[]>(capabilitiesForMode(DEFAULT_INSTANCE_MODE));
	let instanceName = $state(PRODUCT_NAME);
	let hasFetched = $state(false);
	let loading = false;

	return {
		get mode() {
			return mode;
		},
		get capabilities() {
			return capabilities;
		},
		get instanceName() {
			return instanceName;
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
		setInstanceName(next: string) {
			instanceName = next.trim() || PRODUCT_NAME;
		},
		async fetch() {
			if (loading) return;
			loading = true;
			try {
				const s = await instanceSettingsApi.get();
				mode = coerceInstanceMode(s.mode);
				capabilities = s.capabilities ?? capabilitiesForMode(s.mode);
				instanceName = s.instance_name?.trim() || PRODUCT_NAME;
				hasFetched = true;
			} catch {
			} finally {
				loading = false;
			}
		},
		reset() {
			mode = DEFAULT_INSTANCE_MODE;
			capabilities = capabilitiesForMode(DEFAULT_INSTANCE_MODE);
			instanceName = PRODUCT_NAME;
			hasFetched = false;
		}
	};
}

export const capabilitiesStore = createCapabilitiesStore();
