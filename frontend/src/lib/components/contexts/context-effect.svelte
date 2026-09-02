<script lang="ts">
	import { untrack } from 'svelte';
	import * as Select from '$lib/components/ui/select';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { targetTypeLabel, type StageConfig } from '$lib/types/scan-engine';

	interface Props {
		contextId: string | null;
	}

	let { contextId }: Props = $props();

	let engineId = $state('');
	let targetType = $state('domain');
	let before = $state<Record<string, StageConfig>>({});
	let after = $state<Record<string, StageConfig>>({});
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	const engines = $derived(scanEnginesStore.engines);
	const engine = $derived(engines.find((e) => e.id === engineId));

	$effect(() => {
		if (!engineId && engines.length) untrack(() => (engineId = engines[0].id));
	});

	$effect(() => {
		const target = targetType;
		const id = contextId;
		const selected = engine;
		if (!selected) return;
		untrack(() => refresh(selected.stages ?? {}, selected.intensity, target, id));
	});

	let token = 0;
	async function refresh(
		stages: Record<string, StageConfig>,
		intensity: string,
		target_type: string,
		ctxId: string | null
	) {
		const mine = ++token;
		isLoading = true;
		error = null;
		try {
			const body = { target_type, intensity: intensity as never, stages };
			const [plain, merged] = await Promise.all([
				scanEnginesApi.preview(body),
				ctxId ? scanEnginesApi.preview({ ...body, context_id: ctxId }) : Promise.resolve(null)
			]);
			if (mine !== token) return;
			before = plain.resolved_stages;
			after = merged?.resolved_stages ?? plain.resolved_stages;
		} catch (e) {
			if (mine === token) error = e instanceof Error ? e.message : 'Preview unavailable';
		} finally {
			if (mine === token) isLoading = false;
		}
	}

	interface Delta {
		stage: string;
		title: string;
		field: string;
		from: unknown;
		to: unknown;
	}

	const deltas = $derived.by<Delta[]>(() => {
		const out: Delta[] = [];
		for (const [stage, config] of Object.entries(after)) {
			const base = before[stage] ?? {};
			const spec = engineCatalogStore.stage(stage);
			for (const [field, value] of Object.entries(config)) {
				if (JSON.stringify(base[field]) === JSON.stringify(value)) continue;
				out.push({ stage, title: spec?.title ?? stage, field, from: base[field], to: value });
			}
		}
		return out;
	});

	const byStage = $derived.by(() => {
		const groups: Record<string, Delta[]> = {};
		for (const d of deltas) (groups[d.stage] ??= []).push(d);
		return Object.entries(groups);
	});
</script>

<div class="wrap">
	<div class="head">
		<Select.Root type="single" value={engineId} onValueChange={(v) => v && (engineId = v)}>
			<Select.Trigger class="h-7 min-w-[150px] text-xs">
				{engine?.name ?? 'Pick an engine'}
			</Select.Trigger>
			<Select.Content>
				{#each engines as e (e.id)}
					<Select.Item value={e.id} label={e.name}>{e.name}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<Select.Root type="single" value={targetType} onValueChange={(v) => v && (targetType = v)}>
			<Select.Trigger class="h-7 w-[104px] text-xs">{targetTypeLabel(targetType)}</Select.Trigger>
			<Select.Content>
				{#each engineCatalogStore.targetTypes as t (t)}
					<Select.Item value={t} label={targetTypeLabel(t)}>{targetTypeLabel(t)}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{#if isLoading}<Spinner size={12} class="text-muted-foreground" />{/if}
	</div>

	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
			{#if error}
				<p class="err">{error}</p>
			{:else if !engines.length}
				<p class="empty">Create a scan engine to see what this context changes.</p>
			{:else if !deltas.length}
				<p class="empty">
					This context changes nothing for <strong>{engine?.name}</strong>. Add a rate override, a
					multiplier or a scope rule and the effect shows up here.
				</p>
			{:else}
				<p class="count">
					{deltas.length} value{deltas.length === 1 ? '' : 's'} change for
					<strong>{engine?.name}</strong>
				</p>
				{#each byStage as [stage, items] (stage)}
					<p class="stage">{items[0].title}</p>
					{#each items as d (d.field)}
						<div class="row">
							<span class="label">{d.field}</span>
							<span class="from">{String(d.from)}</span>
							<span class="arrow">→</span>
							<span class="to">{String(d.to)}</span>
						</div>
					{/each}
				{/each}
			{/if}
		</div>
	</ScrollArea>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
	}
	.head {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
		flex-shrink: 0;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
	}
	.body {
		padding: 10px 12px 16px;
	}
	.empty,
	.err {
		font-size: 12px;
		line-height: 1.5;
		color: var(--muted-foreground);
	}
	.err {
		color: var(--destructive);
	}
	.count {
		font-size: 11px;
		color: var(--muted-foreground);
		margin-bottom: 8px;
	}
	.stage {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted-foreground);
		margin: 11px 0 4px;
	}
	.stage:first-of-type {
		margin-top: 0;
	}
	.row {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 2px 0;
		font-size: 11.5px;
		flex-wrap: wrap;
	}
	.label {
		min-width: 110px;
		color: var(--muted-foreground);
	}
	.from {
		font-family: var(--font-mono, ui-monospace, monospace);
		color: var(--muted-foreground);
		text-decoration: line-through;
		opacity: 0.7;
	}
	.arrow {
		color: var(--muted-foreground);
		opacity: 0.6;
	}
	.to {
		font-family: var(--font-mono, ui-monospace, monospace);
		color: var(--foreground);
		font-weight: 500;
	}
</style>
