import { describe, expect, it } from 'vitest';
import { causeLine, leadNumber } from './lead';

describe('leadNumber', () => {
	it('takes the count a text opens with', () => {
		expect(leadNumber('32 known exploited findings [B1] sit on one server.', 32)).toEqual({
			number: '32',
			rest: 'known exploited findings [B1] sit on one server.'
		});
		expect(leadNumber('1,204 web assets [B1].', 1204)?.number).toBe('1,204');
	});

	it('leaves a text that opens with another number', () => {
		expect(leadNumber('28 sit on one server [B1].', 32)).toBeNull();
		expect(leadNumber('RDP runs on 32 services.', 32)).toBeNull();
		expect(leadNumber('32 findings.', null)).toBeNull();
	});
});

describe('causeLine', () => {
	it('names the groups and says all only when every row is in one', () => {
		const causes = {
			key: 'ip',
			one: 'server',
			many: 'servers',
			prep: 'on',
			mono: true,
			address: true,
			total_groups: 4,
			groups: []
		};
		expect(causeLine(causes, 32)).toBeNull();
		const top = { value: 'x', label: 'x', count: 28, query: null, who: null, details: [] };
		expect(causeLine({ ...causes, groups: [top] }, 32)).toBe('across 4 servers');
		const one = { ...causes, total_groups: 1, groups: [top] };
		expect(causeLine(one, 28)).toBe('all on one server');
		expect(causeLine(one, 32)).toBe('28 on one server');
		expect(causeLine({ ...one, groups: [{ ...top, count: 10000 }] }, 10000, true)).toBe(
			'10,000 on one server'
		);
	});
});
