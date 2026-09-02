<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as Select from '$lib/components/ui/select';
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import type { PreviewPhase } from '$lib/types/scan';
	import { phaseLabel, targetTypeLabel } from '$lib/types/scan-engine';

	interface Props {
		phases: PreviewPhase[];
		targetType: string;
		targetTypes: string[];
		isLoading: boolean;
		error: string | null;
		onTargetTypeChange: (value: string) => void;
	}

	let { phases, targetType, targetTypes, isLoading, error, onTargetTypeChange }: Props = $props();

	const running = $derived(phases.flatMap((p) => p.tools).filter((t) => t.status === 'will_run'));
	const needsKey = $derived(
		phases.flatMap((p) => p.tools).filter((t) => t.status === 'skipped_needs_key')
	);

	function detail(tool: PreviewPhase['tools'][number]): string {
		const bits: string[] = [];
		if (tool.rate) bits.push(`${tool.rate}/s`);
		if (tool.threads) bits.push(`${tool.threads} threads`);
		if (tool.timeout) bits.push(`${tool.timeout}s`);
		return bits.join(' · ');
	}
</script>

<aside class="panel">
	<div class="head">
		<span class="eyebrow">Against a</span>
		<Select.Root type="single" value={targetType} onValueChange={(v) => v && onTargetTypeChange(v)}>
			<Select.Trigger class="h-7 w-[110px] text-xs">{targetTypeLabel(targetType)}</Select.Trigger>
			<Select.Content>
				{#each targetTypes as type (type)}
					<Select.Item value={type} label={targetTypeLabel(type)}>
						{targetTypeLabel(type)}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<span class="eyebrow">target</span>
	</div>

	<div class="count">
		{#if isLoading && !phases.length}
			<Spinner size={13} class="text-muted-foreground" />
		{:else}
			<strong>{running.length}</strong>
			<span>{running.length === 1 ? 'stage runs' : 'stages run'}</span>
		{/if}
	</div>

	<ScrollArea class="min-h-0 flex-1">
		<div class="list">
			{#if error}
				<p class="error">{error}</p>
			{/if}

			{#each phases as phase (phase.phase)}
				{#if phase.tools.length}
					<p class="phase">{phaseLabel(phase.phase)}</p>
					{#each phase.tools as tool (tool.capability)}
						<div class="item" class:off={tool.status !== 'will_run'}>
							<span class="mark">
								{#if tool.status === 'will_run'}
									<Check size={12} />
								{:else if tool.status === 'skipped_needs_key'}
									<TriangleAlert size={12} />
								{:else}
									<Minus size={12} />
								{/if}
							</span>
							<span class="body">
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
				{/if}
			{/each}
		</div>
	</ScrollArea>

	{#if needsKey.length}
		<div class="foot">
			<TriangleAlert size={12} class="shrink-0 text-warning" />
			<span>{needsKey.length} stage{needsKey.length === 1 ? '' : 's'} need an API key</span>
		</div>
	{/if}
</aside>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		min-height: 0;
		width: 300px;
		flex-shrink: 0;
		border-left: 1px solid var(--border);
		background: var(--card);
	}

	.head {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
		padding: 12px 14px 10px;
	}
	.eyebrow {
		font-size: 11px;
		color: var(--muted-foreground);
	}

	.count {
		display: flex;
		align-items: baseline;
		gap: 5px;
		padding: 0 14px 12px;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
		color: var(--muted-foreground);
	}
	.count strong {
		font-size: 20px;
		font-weight: 600;
		color: var(--foreground);
		line-height: 1;
	}

	.list {
		padding: 10px 14px 14px;
	}
	.phase {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted-foreground);
		margin: 10px 0 6px;
	}
	.phase:first-child {
		margin-top: 0;
	}

	.item {
		display: flex;
		gap: 7px;
		padding: 4px 0;
	}
	.mark {
		display: flex;
		align-items: center;
		height: 16px;
		flex-shrink: 0;
		color: var(--success);
	}
	.item.off .mark {
		color: var(--muted-foreground);
		opacity: 0.6;
	}
	.body {
		display: flex;
		flex-direction: column;
		min-width: 0;
		gap: 1px;
	}
	.name {
		font-size: 12px;
		line-height: 16px;
	}
	.item.off .name {
		color: var(--muted-foreground);
	}
	.sub {
		font-size: 10.5px;
		line-height: 1.35;
		color: var(--muted-foreground);
	}

	.error {
		font-size: 11px;
		color: var(--destructive);
	}

	.foot {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 9px 14px;
		border-top: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted-foreground);
	}
</style>
