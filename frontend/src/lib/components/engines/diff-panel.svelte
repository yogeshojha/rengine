<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { stringify } from 'yaml';
	import type { EngineCatalog, StageConfig } from '$lib/types/scan-engine';

	interface Props {
		stages: Record<string, StageConfig>;
		catalog: EngineCatalog | null;
	}

	let { stages, catalog }: Props = $props();

	interface Change {
		stage: string;
		title: string;
		field: string;
		label: string;
		from: string;
		to: string;
	}

	function render(value: unknown): string {
		if (value === undefined) return '—';
		if (Array.isArray(value)) return value.length ? value.join(', ') : '(none)';
		if (typeof value === 'string') return value === '' ? '(empty)' : value;
		return stringify(value).trim();
	}

	const changes = $derived.by<Change[]>(() => {
		const out: Change[] = [];
		for (const spec of catalog?.stages ?? []) {
			const config = stages?.[spec.name] ?? {};
			for (const field of spec.fields) {
				const value = config[field.name];
				if (value === undefined) continue;
				if (JSON.stringify(value) === JSON.stringify(spec.defaults[field.name])) continue;
				out.push({
					stage: spec.name,
					title: spec.title,
					field: field.name,
					label: field.title,
					from: render(spec.defaults[field.name]),
					to: render(value)
				});
			}
		}
		return out;
	});

	const byStage = $derived.by(() => {
		const groups: Record<string, Change[]> = {};
		for (const change of changes) (groups[change.stage] ??= []).push(change);
		return Object.entries(groups);
	});
</script>

<div class="wrap">
	<div class="head">
		{#if changes.length}
			{changes.length} setting{changes.length === 1 ? '' : 's'} differ from stage defaults
		{:else}
			Matches stage defaults
		{/if}
	</div>
	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
			{#if !changes.length}
				<p class="empty">
					Every setting in this engine matches its stage default. Anything changed is listed here.
				</p>
			{/if}
			{#each byStage as [stage, items] (stage)}
				<p class="stage">{items[0].title}</p>
				{#each items as change (change.field)}
					<div class="row">
						<span class="label">{change.label}</span>
						<span class="from">{change.from}</span>
						<span class="arrow">→</span>
						<span class="to">{change.to}</span>
					</div>
				{/each}
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
	.head {
		flex-shrink: 0;
		padding: 9px 14px;
		border-bottom: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted-foreground);
	}
	.body {
		padding: 10px 14px 16px;
	}
	.empty {
		font-size: 12px;
		color: var(--muted-foreground);
		line-height: 1.5;
	}
	.stage {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted-foreground);
		margin: 12px 0 5px;
	}
	.stage:first-child {
		margin-top: 0;
	}
	.row {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 3px 0;
		font-size: 11.5px;
		flex-wrap: wrap;
	}
	.label {
		min-width: 120px;
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
