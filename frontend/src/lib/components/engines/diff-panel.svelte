<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { stringify } from 'yaml';
	import type { EngineCatalog, StageConfig } from '$lib/types/scan-engine';
	import { overridesOf } from '$lib/utilities/engine-yaml';

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
		if (Array.isArray(value)) return value.length ? value.join(', ') : 'None';
		if (typeof value === 'string') return value === '' ? 'Empty' : value;
		return stringify(value).trim();
	}

	const changes = $derived.by<Change[]>(() => {
		const out: Change[] = [];
		for (const spec of catalog?.stages ?? []) {
			const overrides = overridesOf(stages?.[spec.name] ?? {}, spec.defaults);
			for (const field of spec.fields.filter((f) => f.name in overrides)) {
				const value = overrides[field.name];
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
			{changes.length === 1 ? '1 setting differs' : `${changes.length} settings differ`} from stage defaults
		{:else}
			Matches stage defaults
		{/if}
	</div>
	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
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
		padding: calc(var(--spacing) * 2) calc(var(--spacing) * 3.5);
		border-bottom: 1px solid var(--border);
		font-size: var(--text-2xs);
		color: var(--muted-foreground);
	}
	.body {
		padding: calc(var(--spacing) * 2.5) calc(var(--spacing) * 3.5) calc(var(--spacing) * 4);
	}
	.stage {
		font-size: var(--text-2xs);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.025em;
		color: var(--muted-foreground);
		margin: calc(var(--spacing) * 3) 0 calc(var(--spacing) * 1);
	}
	.stage:first-child {
		margin-top: 0;
	}
	.row {
		display: flex;
		align-items: baseline;
		gap: calc(var(--spacing) * 1.5);
		padding: calc(var(--spacing) * 0.5) 0;
		font-size: var(--text-xs);
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
