<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ScreenshotThumb from '$lib/components/scans/results/screenshot-thumb.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { VISUAL_FIELD_LABELS, VISUAL_MAX_DISTANCE } from '$lib/config/whats-new';
	import { visualChange } from '$lib/utilities/whats-new';
	import type { VisualPair } from '$lib/types/whats-new';

	interface Props {
		pairs: VisualPair[];
		cursor?: number;
		onOpen: (pair: VisualPair) => void;
		onCompare: (index: number) => void;
		onScan: (pair: VisualPair) => void;
		onPick?: (index: number) => void;
	}

	let { pairs, cursor = -1, onOpen, onCompare, onScan, onPick }: Props = $props();

	const METER = 5;
	const level = (d: number) =>
		Math.min(METER, Math.max(1, Math.ceil((d / VISUAL_MAX_DISTANCE) * METER * 2)));
</script>

<div class="grid grid-cols-[repeat(auto-fill,minmax(21rem,1fr))] gap-3">
	{#each pairs as pair, i (pair.id)}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
		<article
			data-visual-card={i}
			class="group/pair flex flex-col overflow-clip rounded-xl border bg-card transition-shadow {cursor ===
			i
				? 'ring-2 ring-ring'
				: ''}"
			onclick={() => onPick?.(i)}
		>
			<div class="flex items-center gap-2 border-b px-3 py-2">
				<button
					type="button"
					class="min-w-0 flex-1 truncate text-left font-mono text-sm hover:text-primary"
					onclick={() => onOpen(pair)}
				>
					{pair.host}
				</button>
				<CopyButton
					value={pair.host}
					class="size-7 opacity-0 group-hover/pair:opacity-100 focus-visible:opacity-100"
				/>
				<a
					href={ROUTES.target(pair.target_id)}
					class="truncate text-2xs text-muted-foreground hover:text-foreground"
				>
					{pair.target_value}
				</a>
			</div>
			<button
				type="button"
				class="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 pt-3 text-left focus-visible:outline-none"
				aria-label="Compare {pair.host} before and after"
				onclick={() => onCompare(i)}
			>
				<ScreenshotThumb
					path={pair.before_path}
					alt="{pair.host} before"
					class="aspect-[16/10] w-full"
					interactive={false}
				/>
				<ArrowRight class="size-4 text-muted-foreground" />
				<ScreenshotThumb
					path={pair.after_path}
					alt="{pair.host} after"
					class="aspect-[16/10] w-full"
					interactive={false}
				/>
			</button>
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-3 pt-2 pb-3">
				<span
					class="flex items-center gap-0.5"
					aria-label="Distance {pair.distance} of {VISUAL_MAX_DISTANCE}"
				>
					{#each { length: METER } as _, i (i)}
						<span
							class="h-2 w-1.5 rounded-[1px] {i < level(pair.distance) ? '' : 'bg-muted'}"
							style={i < level(pair.distance) ? 'background: var(--series)' : ''}
						></span>
					{/each}
				</span>
				<span class="text-2xs text-muted-foreground tabular-nums">{pair.distance}</span>
				{#if pair.silent}
					<Badge variant="warning">Silent redeploy</Badge>
				{:else}
					{#each pair.moved as field (field)}
						<Badge variant="secondary" class="max-w-full font-normal">
							<span class="truncate"
								>{VISUAL_FIELD_LABELS[field] ?? field} · {visualChange(pair, field)}</span
							>
						</Badge>
					{/each}
				{/if}
				<span class="ml-auto flex items-center gap-0.5">
					<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => onCompare(i)}>
						Wipe
					</Button>
					<Button
						variant="ghost"
						size="sm"
						class="h-7 px-2 text-xs"
						href={ROUTES.compare(pair.scan_id, pair.previous_scan_id)}
					>
						Compare runs
					</Button>
					<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => onScan(pair)}>
						Scan
					</Button>
				</span>
			</div>
		</article>
	{/each}
</div>
