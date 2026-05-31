// Shared signal/sort types + the per-row expiry helper (filtering/sort/KPIs are server-side)

import { type Target } from '$lib/types/target';
import { getExpirationUrgency, type ExpirationUrgency } from '$lib/utilities/dates';

export type SortKey = 'updated' | 'created' | 'name' | 'type' | 'expiry' | 'enrichment';
export type SortDir = 'asc' | 'desc';
export type SignalFilter = 'expiring' | 'attention' | 'awaiting' | 'enriched';

export interface TargetSummary {
	total: number;
	expiring: number;
	attention: number;
	awaiting: number;
	enriched: number;
}

export interface ExpirySignal {
	urgency: ExpirationUrgency;
	days: number | null;
	date: string | null;
}

export function getExpirySignal(target: Target): ExpirySignal {
	const date = target.whois?.expiration_date ?? null;
	const urgency = getExpirationUrgency(date);
	let days: number | null = null;
	if (date) {
		days = Math.floor((new Date(date).getTime() - Date.now()) / 86_400_000);
	}
	return { urgency, days, date };
}
