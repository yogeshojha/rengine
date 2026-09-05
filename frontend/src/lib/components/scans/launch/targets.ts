import { targetsApi } from '$lib/api/targets';
import type { TargetChip } from './launch-state.svelte';

export const INVALID_TARGET_MESSAGE = 'Unrecognised target';
export const TARGET_FORMATS = 'Enter a domain, IP address, CIDR range, URL or ASN.';

export function splitTargetInput(raw: string): string[] {
	return [
		...new Set(
			raw
				.split(/[\s,;]+/)
				.map((v) => v.trim())
				.filter(Boolean)
		)
	];
}

export function chipFor(target: {
	id: string;
	target_value: string;
	target_type: string;
}): TargetChip {
	return { key: target.id, id: target.id, value: target.target_value, type: target.target_type };
}

// An existing target when the value is already in the project, otherwise a chip to create on launch.
export async function resolveTargetValue(
	value: string,
	projectSlug: string
): Promise<TargetChip | null> {
	const check = await targetsApi.validate({ target_value: value });
	if (!check.valid || !check.target_type) return null;
	const normalized = check.target_value || value;
	const matches = await targetsApi.searchByValue(normalized, projectSlug).catch(() => []);
	const exact = matches.find((t) => t.target_value.toLowerCase() === normalized.toLowerCase());
	if (exact) return chipFor(exact);
	return {
		key: `new:${normalized.toLowerCase()}`,
		id: null,
		value: normalized,
		type: check.target_type
	};
}
