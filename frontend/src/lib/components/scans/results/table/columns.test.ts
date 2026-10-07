import { describe, expect, it } from 'vitest';
import { columnCell, columnPx, fitColumns, type TableColumn } from './columns';
import { WEB_ASSET_COLUMNS, WEB_ASSET_LEAD_COLUMNS } from '../web-assets/columns';

const col = (key: string, width: string, grow?: boolean): TableColumn => ({
	key,
	label: key,
	width,
	grow
});

describe('columnPx', () => {
	it('reads fixed, rem and px widths', () => {
		expect(columnPx(col('a', 'w-52'))).toBe(208);
		expect(columnPx(col('a', 'w-[5.5rem]'))).toBe(88);
		expect(columnPx(col('a', 'w-[72px] shrink-0'))).toBe(72);
	});

	it('lets the sm: width win, as it does at desktop widths', () => {
		expect(columnPx(col('a', 'min-w-0 flex-1 contain-inline-size sm:w-72 sm:flex-none'))).toBe(288);
		expect(columnPx(col('a', 'min-w-0 flex-[3] contain-inline-size sm:min-w-56'))).toBe(224);
	});

	it('takes a growing column at its minimum and ignores max-w', () => {
		expect(columnPx(col('a', 'min-w-56 max-w-[20rem]', true))).toBe(224);
	});
});

describe('fitColumns', () => {
	const lead = [col('name', 'w-40')];
	const cols = [col('a', 'w-40'), col('b', 'w-40'), col('c', 'w-40')];

	it('keeps everything until the width is measured', () => {
		expect(fitColumns(cols, 0, lead)).toEqual(cols);
	});

	it('folds columns from the end when there is no room', () => {
		// chrome 32 + 92 + 28, lead 160 + 12 = 324 before the columns; each column needs 172
		expect(fitColumns(cols, 324 + 172 * 3, lead).map((c) => c.key)).toEqual(['a', 'b', 'c']);
		expect(fitColumns(cols, 324 + 172 * 2, lead).map((c) => c.key)).toEqual(['a', 'b']);
		expect(fitColumns(cols, 324 + 100, lead)).toEqual([]);
	});

	it('fits the default web asset columns in a 1440px window', () => {
		const shown = fitColumns(
			WEB_ASSET_COLUMNS.filter((c) => ['tech', 'ip', 'ports', 'screenshot'].includes(c.key)),
			1126,
			WEB_ASSET_LEAD_COLUMNS
		);
		expect(shown.map((c) => c.key)).toEqual(['tech', 'ip', 'ports']);
	});
});

describe('columnCell', () => {
	it('contains a growing column so it never widens the row past the card', () => {
		expect(columnCell(col('a', 'min-w-56', true))).toContain('contain-inline-size');
		expect(columnCell(col('a', 'min-w-56', true))).not.toContain('min-w-0');
	});
});
