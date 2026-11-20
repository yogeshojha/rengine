import { EXPIRY_LABELS } from '$lib/config/access-keys';
import { EXAMPLE_BASE_URL, PROJECT_VARIABLE } from '$lib/config/api-reference';
import type { AccessKey, ReferenceOperation } from '$lib/types/access-key';
import {
	expiresSoon,
	formatShortDate,
	MS_PER_DAY,
	untilTime,
	type ExpiryTone
} from '$lib/utilities/dates';
import { plural } from '$lib/utilities/strings';

export function keyExpiry(
	key: Pick<AccessKey, 'expires_at' | 'expired'>,
	now = Date.now()
): { label: string; tone: ExpiryTone } {
	if (!key.expires_at) return { label: EXPIRY_LABELS.get(null) ?? '', tone: 'none' };
	const diff = new Date(key.expires_at).getTime() - now;
	if (key.expired || diff <= 0) return { label: 'Expired', tone: 'expired' };
	if (!expiresSoon(key.expires_at, now))
		return { label: formatShortDate(key.expires_at), tone: 'none' };
	const days = Math.floor(diff / MS_PER_DAY);
	if (days < 1) return { label: untilTime(key.expires_at) ?? 'Expired', tone: 'soon' };
	return { label: `in ${plural(days, 'day')}`, tone: 'soon' };
}

/** A server-built request sent to this origin, in the open project when one is given. */
export function requestFor(curl: string, origin: string, projectId?: string | null): string {
	const sent = curl.replace(EXAMPLE_BASE_URL, origin);
	return projectId ? sent.replaceAll(PROJECT_VARIABLE, projectId) : sent;
}

/** The keys that count toward MAX_ACCESS_KEYS. */
export const activeKeys = (keys: Pick<AccessKey, 'expired'>[]): number =>
	keys.filter((k) => !k.expired).length;

export const operationKey = (op: Pick<ReferenceOperation, 'method' | 'path'>) =>
	`${op.method.toUpperCase()} ${op.path}`;
