import { describe, expect, it } from 'vitest';
import { FIT_ORDER, TCOL, TCOL_PX, fitColumns } from './columns';

const ALL = [...FIT_ORDER];

describe('target list columns', () => {
	it('declares the pixel width its class renders', () => {
		for (const column of FIT_ORDER) {
			expect(TCOL[column]).toContain(`w-[${TCOL_PX[column]}px]`);
		}
	});

	it('fits columns in order until the target column would shrink below its minimum', () => {
		expect([...fitColumns(1126, ALL)]).toEqual(['findings', 'run', 'assets', 'change']);
	});

	it('gives the room of a hidden column to the next one', () => {
		const chosen = ALL.filter((c) => c !== 'assets');
		expect(fitColumns(1126, chosen).has('organizations')).toBe(true);
	});

	it('never shows a column that was not chosen', () => {
		expect(fitColumns(4000, ['tags'])).toEqual(new Set(['tags']));
	});

	it('fits nothing before the width is measured', () => {
		expect(fitColumns(0, ALL).size).toBe(0);
	});
});
