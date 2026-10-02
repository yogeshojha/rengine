<script lang="ts">
	import { FireOn } from '$lib/config/tripwires';

	interface Props {
		mode: string;
		class?: string;
	}

	let { mode, class: klass = '' }: Props = $props();

	const ROWS = [6, 14, 22];
	const LEFT = 3;
	const RIGHT = 41;
	const W = 20;
	const H = 5;

	type Cell = 'absent' | 'plain' | 'hollow' | 'fires';

	let cells = $derived.by((): { left: Cell[]; right: Cell[] } => {
		if (mode === FireOn.BecomesTrue) {
			return { left: ['plain', 'hollow', 'plain'], right: ['plain', 'fires', 'plain'] };
		}
		if (mode === FireOn.Matches) {
			return { left: ['plain', 'fires', 'absent'], right: ['plain', 'fires', 'absent'] };
		}
		return { left: ['plain', 'plain', 'absent'], right: ['plain', 'plain', 'fires'] };
	});
</script>

<svg viewBox="0 0 64 32" class="h-8 w-16 shrink-0 {klass}" aria-hidden="true">
	{#each [LEFT, RIGHT] as x, column (x)}
		<rect {x} y="1" width={W} height="30" rx="3" class="fill-none stroke-border" stroke-width="1" />
		{#each ROWS as y, row (y)}
			{@const cell = (column === 0 ? cells.left : cells.right)[row]}
			{#if cell === 'plain'}
				<rect x={x + 3} {y} width={W - 6} height={H} rx="1.5" class="fill-muted-foreground/45" />
			{:else if cell === 'hollow'}
				<rect
					x={x + 3.5}
					y={y + 0.5}
					width={W - 7}
					height={H - 1}
					rx="1.5"
					class="fill-none stroke-muted-foreground/70"
					stroke-width="1"
				/>
			{:else if cell === 'fires'}
				<rect x={x + 3} {y} width={W - 6} height={H} rx="1.5" class="fill-info" />
			{/if}
		{/each}
	{/each}
	<path
		d="M26 16h11m-3-3l3 3-3 3"
		class="fill-none stroke-muted-foreground"
		stroke-width="1.5"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
</svg>
