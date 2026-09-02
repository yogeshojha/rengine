<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as Select from '$lib/components/ui/select';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { stringify } from 'yaml';
	import { targetTypeLabel, type StageConfig } from '$lib/types/scan-engine';

	interface Props {
		resolved: Record<string, StageConfig>;
		warnings: string[];
		targetType: string;
		targetTypes: string[];
		isLoading: boolean;
		error: string | null;
		onTargetTypeChange: (value: string) => void;
	}

	let { resolved, warnings, targetType, targetTypes, isLoading, error, onTargetTypeChange }: Props =
		$props();

	const text = $derived(
		Object.keys(resolved ?? {}).length ? stringify(resolved, { indent: 2, lineWidth: 0 }) : ''
	);
</script>

<div class="wrap">
	<div class="head">
		<span class="note">What the worker receives for a</span>
		<Select.Root type="single" value={targetType} onValueChange={(v) => v && onTargetTypeChange(v)}>
			<Select.Trigger class="h-6 w-[104px] text-[11px]"
				>{targetTypeLabel(targetType)}</Select.Trigger
			>
			<Select.Content>
				{#each targetTypes as type (type)}
					<Select.Item value={type} label={targetTypeLabel(type)}>
						{targetTypeLabel(type)}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<span class="note">target</span>
	</div>

	{#if warnings.length}
		<div class="warnings">
			{#each warnings as warning (warning)}
				<p><TriangleAlert size={11} class="shrink-0" />{warning}</p>
			{/each}
		</div>
	{/if}

	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
			{#if error}
				<p class="err">{error}</p>
			{:else if isLoading && !text}
				<Spinner size={14} class="text-muted-foreground" />
			{:else}
				<pre>{text}</pre>
				<p class="foot">
					Defaults filled in, scan-context multipliers and passive gating applied. This is the exact
					config each stage reads at run time.
				</p>
			{/if}
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
	.head {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
		flex-shrink: 0;
		padding: 7px 12px;
		border-bottom: 1px solid var(--border);
	}
	.note {
		font-size: 11px;
		color: var(--muted-foreground);
	}
	.warnings {
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--warning) 7%, transparent);
		padding: 6px 12px;
	}
	.warnings p {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		color: var(--warning);
		line-height: 1.5;
	}
	.body {
		padding: 10px 12px 16px;
	}
	pre {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 11.5px;
		line-height: 1.6;
		color: var(--foreground);
		white-space: pre;
	}
	.foot {
		margin-top: 12px;
		padding-top: 10px;
		border-top: 1px solid var(--border);
		font-size: 11px;
		line-height: 1.5;
		color: var(--muted-foreground);
	}
	.err {
		font-size: 11px;
		color: var(--destructive);
	}
</style>
