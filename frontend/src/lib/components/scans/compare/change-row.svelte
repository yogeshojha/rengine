<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import { cn } from '$lib/utils';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import VerbRail from './verb-rail.svelte';
	import { SIGNAL_TONE_CLASS, signalSpec } from '$lib/config/compare';
	import { surfaceSpec } from '$lib/config/surface';
	import type { ChangeRow } from '$lib/types/compare';

	interface Props {
		row: ChangeRow;
		showDimension?: boolean;
		selected?: boolean;
		onOpen: (row: ChangeRow) => void;
	}

	let { row, showDimension = false, selected = false, onOpen }: Props = $props();

	let signal = $derived(signalSpec(row.signal));
	let spec = $derived(surfaceSpec(row.dimension));
	let fields = $derived(row.fields.slice(0, 4));
	let rest = $derived(row.fields.length - fields.length);
</script>

<button
	type="button"
	onclick={() => onOpen(row)}
	class={cn(
		'grid w-full grid-cols-[auto_minmax(0,1fr)] items-stretch gap-x-3 border-b px-4 py-2.5 text-left transition-colors last:border-b-0 sm:px-5',
		selected ? 'bg-accent/60' : 'hover:bg-accent/40'
	)}
>
	<VerbRail verb={row.verb} />

	<span class="flex min-w-0 flex-col gap-1">
		<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
			{#if row.severity}
				<SeverityMark severity={row.severity} />
			{/if}
			<span class="min-w-0 font-mono text-[13px] break-all">{row.title}</span>
			{#if row.is_kev}
				<span
					class="inline-flex shrink-0 items-center gap-1 rounded border border-destructive/30 bg-destructive/10 px-1.5 text-[10px] font-medium text-destructive"
				>
					<Flame class="size-2.5" /> KEV
				</span>
			{/if}
			{#if row.sensitive}
				<span
					class="shrink-0 rounded border border-warning/30 bg-warning/10 px-1.5 text-[10px] font-medium text-warning"
				>
					sensitive
				</span>
			{/if}

			<span
				class={cn(
					'ml-auto flex shrink-0 items-center gap-1.5 text-[11px] font-medium',
					SIGNAL_TONE_CLASS[signal.tone]
				)}
			>
				<signal.icon class="size-3.5" />
				{signal.label}
			</span>
		</span>

		<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px]">
			{#if showDimension && spec}
				<span class="inline-flex shrink-0 items-center gap-1 text-muted-foreground">
					<spec.icon class="size-3" />
					{spec.label}
				</span>
				{#if row.subtitle}<span class="text-muted-foreground/40">·</span>{/if}
			{/if}
			{#if row.subtitle}
				<span class="min-w-0 truncate text-muted-foreground">{row.subtitle}</span>
			{/if}
		</span>

		{#if fields.length}
			<span class="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px]">
				{#each fields as f (f.field)}
					<span class="inline-flex items-center gap-1">
						<span class="text-muted-foreground">{f.label}</span>
						{#if f.before !== null && f.after !== null}
							<span class="text-muted-foreground line-through">{f.before}</span>
							<span class="text-muted-foreground/60">→</span>
							<span class="font-medium">{f.after}</span>
						{:else if f.after !== null}
							<span class="font-medium">{f.after}</span>
						{:else}
							<span class="text-muted-foreground">gone</span>
						{/if}
					</span>
				{/each}
				{#if rest > 0}
					<span class="text-muted-foreground">+{rest} more</span>
				{/if}
			</span>
		{/if}
	</span>
</button>
