<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import type { ScanTrendPoint } from '$lib/types/scan';
	import { formatDateTime } from '$lib/utilities/dates';
	import { historyPrefs } from './prefs.svelte';

	const W = 72;
	const H = 20;
	const PAD = 2.5;

	interface Props {
		points: ScanTrendPoint[];
		current: string;
		onJump: (scanId: string) => void;
	}

	let { points, current, onJump }: Props = $props();

	let values = $derived(
		points.map((p) => p.critical + p.high + (historyPrefs.showMedium ? p.medium : 0))
	);
	let max = $derived(Math.max(1, ...values));
	let xy = $derived(
		values.map((v, i) => ({
			x: points.length === 1 ? W / 2 : PAD + (i * (W - 2 * PAD)) / (points.length - 1),
			y: H - PAD - (v / max) * (H - 2 * PAD)
		}))
	);
	let line = $derived(
		xy.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join('')
	);
	let area = $derived(
		xy.length ? `${line}L${xy[xy.length - 1].x.toFixed(1)},${H}L${xy[0].x.toFixed(1)},${H}Z` : ''
	);
</script>

{#if points.length >= 2}
	<svg
		width={W}
		height={H}
		viewBox="0 0 {W} {H}"
		class="shrink-0 overflow-visible"
		role="img"
		aria-label="Findings over the last {points.length} completed runs"
	>
		<path d={area} fill="var(--series)" fill-opacity="0.12" />
		<path d={line} fill="none" stroke="var(--series)" stroke-width="1.25" stroke-linejoin="round" />
		{#each points as p, i (p.scan_id)}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<circle
							{...props}
							cx={xy[i].x}
							cy={xy[i].y}
							r={p.scan_id === current ? 2.75 : 1.75}
							fill={p.scan_id === current ? 'var(--foreground)' : 'var(--series)'}
							stroke="var(--background)"
							stroke-width="1"
							class="cursor-pointer outline-none"
							role="button"
							tabindex="-1"
							aria-label="Run of {formatDateTime(p.started_at)}"
							onclick={(e: MouseEvent) => {
								e.stopPropagation();
								onJump(p.scan_id);
							}}
							onkeydown={() => {}}
						/>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="font-mono text-2xs">
					{formatDateTime(p.started_at)} · {p.critical} critical · {p.high} high{historyPrefs.showMedium
						? ` · ${p.medium} medium`
						: ''}
				</Tooltip.Content>
			</Tooltip.Root>
		{/each}
	</svg>
{/if}
