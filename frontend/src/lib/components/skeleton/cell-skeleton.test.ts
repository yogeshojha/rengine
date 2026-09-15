import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import CellSkeleton from '$lib/components/skeleton/cell-skeleton.svelte';
import PanelSkeleton from '$lib/components/skeleton/panel-skeleton.svelte';
import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
import type { SkeletonShape } from '$lib/components/skeleton/shapes';

const SHAPES: SkeletonShape[] = [
	'text',
	'bars',
	'ranked',
	'list',
	'meters',
	'donut',
	'map',
	'stat',
	'board'
];

describe('cell skeleton', () => {
	it.each(SHAPES)('renders the %s shape', (shape) => {
		expect(render(CellSkeleton, { props: { shape } }).body).toContain('animate-pulse');
	});

	it('renders the panel and row shapes', () => {
		expect(render(PanelSkeleton, { props: { stats: true, meter: true } }).body).toContain(
			'animate-pulse'
		);
		expect(render(RowSkeleton, { props: {} }).body).toContain('animate-pulse');
	});
});
