<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import type { PreviewPhase, PreviewTool } from '$lib/types/scan';
	import { phaseLabel, type StageCatalogEntry } from '$lib/types/scan-engine';
	import { formatSeconds } from '$lib/utilities/format';

	interface Props {
		phases: PreviewPhase[];
		stages: StageCatalogEntry[];
		isLoading: boolean;
		error: string | null;
	}

	let { phases, stages, isLoading, error }: Props = $props();

	function levelOf(tool: PreviewTool): number {
		return stages.find((s) => s.name === tool.capability)?.level ?? 0;
	}

	function byLevel(phase: PreviewPhase): [number, PreviewTool[]][] {
		const groups: Record<number, PreviewTool[]> = {};
		for (const tool of phase.tools) (groups[levelOf(tool)] ??= []).push(tool);
		return Object.entries(groups)
			.map(([level, tools]): [number, PreviewTool[]] => [Number(level), tools])
			.sort((a, b) => a[0] - b[0]);
	}

	function detail(tool: PreviewTool): string {
		const bits: string[] = [];
		if (tool.rate) bits.push(`${tool.rate}/s`);
		if (tool.threads) bits.push(`${tool.threads} threads`);
		if (tool.timeout) bits.push(formatSeconds(tool.timeout));
		return bits.join(' · ');
	}

	const visible = $derived(phases.filter((p) => p.tools.length));
</script>

<div class="wrap">
	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
			{#if error}
				<p class="error">{error}</p>
			{:else if isLoading && !phases.length}
				<div class="flex flex-col gap-2">
					{#each Array(8) as _, i (i)}
						<Skeleton class="h-3.5 {i % 2 ? 'w-2/3' : 'w-full'}" />
					{/each}
				</div>
			{/if}

			{#each visible as phase, pi (phase.phase)}
				{@const run = phase.tools.filter((t) => t.status === 'will_run').length}
				<section class="phase">
					<header class="phase-head">
						<h3>{phaseLabel(phase.phase)}</h3>
						<span class="count">{run}/{phase.tools.length} run</span>
					</header>

					{#each byLevel(phase) as [level, tools], li (level)}
						{#if li > 0}
							<div class="link" aria-hidden="true"></div>
						{/if}
						<div class="level">
							<div class="items">
								{#each tools as tool (tool.capability)}
									<div class="item" data-status={tool.status}>
										<span class="mark">
											{#if tool.status === 'will_run'}
												<Check size={12} />
											{:else if tool.status === 'skipped_needs_key'}
												<TriangleAlert size={12} />
											{:else}
												<Minus size={12} />
											{/if}
										</span>
										<span class="text">
											<span class="name">{tool.label}</span>
											{#if tool.status === 'will_run'}
												{@const d = detail(tool)}
												{#if d}<span class="sub">{d}</span>{/if}
											{:else if tool.reason}
												<span class="sub">{tool.reason}</span>
											{/if}
										</span>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</section>
				{#if pi < visible.length - 1}
					<div class="link phase-link" aria-hidden="true"></div>
				{/if}
			{/each}
		</div>
	</ScrollArea>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.body {
		padding: calc(var(--spacing) * 3.5) calc(var(--spacing) * 3.5) calc(var(--spacing) * 5);
	}
	.error {
		font-size: var(--text-2xs);
		color: var(--destructive);
	}

	.phase {
		border: 1px solid var(--border);
		border-radius: 0.6rem;
		background: color-mix(in oklch, var(--muted) 30%, transparent);
		padding: calc(var(--spacing) * 2.5) calc(var(--spacing) * 3) calc(var(--spacing) * 3);
	}
	.phase-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: calc(var(--spacing) * 2);
		margin-bottom: calc(var(--spacing) * 2);
	}
	.phase-head h3 {
		font-size: var(--text-2xs);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.025em;
		color: var(--muted-foreground);
	}
	.count {
		font-size: var(--text-2xs);
		color: var(--muted-foreground);
		font-variant-numeric: tabular-nums;
	}
	.link {
		width: 3px;
		height: 14px;
		margin-left: calc(var(--spacing) * 3);
		background: radial-gradient(
				circle,
				color-mix(in oklch, var(--muted-foreground) 65%, transparent) 1px,
				transparent 1.6px
			)
			center / 3px 5px repeat-y;
	}
	.link.phase-link {
		height: 20px;
		margin-left: calc(var(--spacing) * 6);
	}

	.level {
		display: flex;
		align-items: flex-start;
	}
	.items {
		display: flex;
		flex-wrap: wrap;
		gap: calc(var(--spacing) * 1.5);
		min-width: 0;
		flex: 1;
	}
	.item {
		display: flex;
		gap: calc(var(--spacing) * 1.5);
		align-items: flex-start;
		padding: calc(var(--spacing) * 1) calc(var(--spacing) * 2) calc(var(--spacing) * 1)
			calc(var(--spacing) * 1.5);
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--card);
		min-width: 0;
	}
	.item[data-status='will_run'] {
		border-color: color-mix(in oklch, var(--primary) 35%, var(--border));
	}
	.item:not([data-status='will_run']) {
		border-style: dashed;
		background: transparent;
	}
	.mark {
		display: flex;
		align-items: center;
		height: 16px;
		flex-shrink: 0;
		color: var(--success);
	}
	.item[data-status='skipped_needs_key'] .mark {
		color: var(--warning);
	}
	.item:not([data-status='will_run']):not([data-status='skipped_needs_key']) .mark {
		color: var(--muted-foreground);
		opacity: 0.6;
	}
	.text {
		display: flex;
		flex-direction: column;
		min-width: 0;
		gap: 1px;
	}
	.name {
		font-size: var(--text-xs);
		line-height: 16px;
	}
	.item:not([data-status='will_run']) .name {
		color: var(--muted-foreground);
	}
	.sub {
		font-size: var(--text-2xs);
		line-height: 1.35;
		color: var(--muted-foreground);
		font-variant-numeric: tabular-nums;
	}
</style>
