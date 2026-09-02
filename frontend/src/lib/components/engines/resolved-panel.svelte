<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { stringify } from 'yaml';
	import YamlPane from './yaml-pane.svelte';
	import { targetTypeLabel, type StageConfig } from '$lib/types/scan-engine';

	interface Props {
		resolved: Record<string, StageConfig>;
		warnings: string[];
		targetType: string;
		isLoading: boolean;
		error: string | null;
	}

	let { resolved, warnings, targetType, isLoading, error }: Props = $props();

	const text = $derived(
		Object.keys(resolved ?? {}).length ? stringify(resolved, { indent: 2, lineWidth: 0 }) : ''
	);
	const stageStates = $derived(
		Object.fromEntries(
			Object.entries(resolved ?? {}).map(([name, cfg]) => [name, Boolean(cfg?.enabled ?? true)])
		)
	);
</script>

<div class="wrap">
	<div class="head">
		The final configuration for a {targetTypeLabel(targetType)} target, with defaults applied, scan context
		multipliers resolved and passive intensity enforced.
	</div>

	{#if warnings.length}
		<div class="warnings">
			{#each warnings as warning (warning)}
				<p><TriangleAlert size={11} class="shrink-0" />{warning}</p>
			{/each}
		</div>
	{/if}

	<div class="editor">
		{#if error}
			<p class="err">{error}</p>
		{:else if isLoading && !text}
			<div class="center"><Spinner size={14} class="text-muted-foreground" /></div>
		{:else}
			<YamlPane value={text} readonly chrome={false} {stageStates} />
		{/if}
	</div>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.head {
		flex-shrink: 0;
		padding: 9px 14px;
		border-bottom: 1px solid var(--border);
		font-size: 11px;
		line-height: 1.5;
		color: var(--muted-foreground);
	}
	.warnings {
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--warning) 7%, transparent);
		padding: 6px 14px;
	}
	.warnings p {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		color: var(--warning);
		line-height: 1.5;
	}
	.editor {
		flex: 1;
		min-height: 0;
	}
	.center {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
	}
	.err {
		padding: 12px 14px;
		font-size: 11px;
		color: var(--destructive);
	}
</style>
