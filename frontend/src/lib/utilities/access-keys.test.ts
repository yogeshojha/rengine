import { describe, expect, it } from 'vitest';
import { activeKeys, keyExpiry, operationKey, requestFor } from './access-keys';
import { formatShortDate } from './dates';

const NOW = Date.parse('2026-11-21T12:00:00Z');
const DAY = 86_400_000;
const at = (ms: number) => new Date(NOW + ms).toISOString();

describe('keyExpiry', () => {
	it('reads no expiry', () => {
		expect(keyExpiry({ expires_at: null, expired: false }, NOW)).toEqual({
			label: 'No expiry',
			tone: 'none'
		});
	});

	it('reads the date past a week and counts whole days inside it', () => {
		expect(keyExpiry({ expires_at: at(90 * DAY - 5000), expired: false }, NOW)).toEqual({
			label: formatShortDate(at(90 * DAY - 5000)),
			tone: 'none'
		});
		expect(keyExpiry({ expires_at: at(DAY + 5000), expired: false }, NOW)).toEqual({
			label: 'in 1 day',
			tone: 'soon'
		});
	});

	it('warns at the same day count as an agent key', () => {
		expect(keyExpiry({ expires_at: at(7 * DAY), expired: false }, NOW)).toEqual({
			label: 'in 7 days',
			tone: 'soon'
		});
		expect(keyExpiry({ expires_at: at(7 * DAY + 5000), expired: false }, NOW).tone).toBe('none');
	});

	it('reads expired from the flag or the clock', () => {
		expect(keyExpiry({ expires_at: at(-DAY), expired: false }, NOW).tone).toBe('expired');
		expect(keyExpiry({ expires_at: at(DAY * 3), expired: true }, NOW)).toEqual({
			label: 'Expired',
			tone: 'expired'
		});
	});
});

describe('requestFor', () => {
	const curl =
		'curl -X POST "https://rengine.example.com/api/v1/subdomains/search?project_id=$PROJECT_ID" \\\n' +
		'  -H "Authorization: Bearer $RENGINE_KEY"';

	it('sends the server request to this origin', () => {
		expect(requestFor(curl, 'https://r.example')).toBe(
			'curl -X POST "https://r.example/api/v1/subdomains/search?project_id=$PROJECT_ID" \\\n' +
				'  -H "Authorization: Bearer $RENGINE_KEY"'
		);
	});

	it('fills the open project and keeps the variable without one', () => {
		expect(requestFor(curl, 'https://r.example', 'p1')).toContain('?project_id=p1"');
		expect(requestFor(curl, 'https://r.example', null)).toContain('?project_id=$PROJECT_ID"');
	});
});

describe('activeKeys', () => {
	it('leaves expired keys out of the count', () => {
		expect(activeKeys([{ expired: false }, { expired: true }, { expired: false }])).toBe(2);
	});
});

describe('operationKey', () => {
	it('joins the method and the path', () => {
		expect(operationKey({ method: 'delete', path: '/api/v1/targets/{target_id}' })).toBe(
			'DELETE /api/v1/targets/{target_id}'
		);
	});
});
