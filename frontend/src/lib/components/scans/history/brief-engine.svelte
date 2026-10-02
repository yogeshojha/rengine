<script lang="ts">
	import { ROUTES } from '$lib/config/routes';
	import { HTTP_PROTOCOL_LABELS } from '$lib/components/contexts/context-summary';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { INTENSITY_LABELS, type Intensity } from '$lib/types/scan-engine';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import { NO_CONTEXT_LABEL } from '$lib/types/scan-context';
	import { formatDateTime } from '$lib/utilities/dates';
	import { durationLabel } from '$lib/utilities/scan-status';
	import { plannedStages } from '$lib/utilities/scan-progress';
	import { plural } from '$lib/utilities/strings';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		scan: ScanRead;
		now: number;
	}

	let { scan, now }: Props = $props();

	$effect(() => {
		engineCatalogStore.fetch();
	});

	let cfg = $derived(scan.execution_config);
	let stages = $derived(plannedStages(scan, engineCatalogStore.stages));
	let exclusions = $derived(
		cfg.excluded_subdomains.length + cfg.excluded_paths.length + cfg.excluded_ips.length
	);
	let facts = $derived<[string, string][]>([
		['Scope', scan.scope === 'focused' ? `Focused · ${scan.seed_count} assets` : 'Full'],
		['Context', scan.context_name ?? NO_CONTEXT_LABEL],
		['Authentication', scan.auth_summary],
		['Protocol', HTTP_PROTOCOL_LABELS[cfg.http_protocol] ?? cfg.http_protocol],
		['Exclusions', exclusions ? plural(exclusions, 'rule') : 'None'],
		[
			'Rate ceiling',
			cfg.global_rate_limit_ceiling ? `${cfg.global_rate_limit_ceiling} req/s` : 'None'
		],
		[
			'Schedule',
			scan.schedule_type
				? (SCHEDULE_TYPE_BADGE[scan.schedule_type as ScheduleType] ?? scan.schedule_type)
				: 'Manual'
		],
		['Started', scan.started_at ? formatDateTime(scan.started_at) : 'Not started'],
		['Duration', durationLabel(scan, now)]
	]);
</script>

<div class="flex flex-col gap-4 py-2">
	<div class="flex flex-wrap items-center gap-3 px-1">
		{#if scan.engine_id}
			<a
				href={ROUTES.engine(scan.engine_id)}
				class="text-xl font-semibold tracking-tight hover:text-primary"
			>
				{scan.engine_name}
			</a>
		{:else}
			<span class="text-xl font-semibold tracking-tight">{scan.engine_name}</span>
		{/if}
		<span class="rounded-full border border-border px-2 py-0.5 text-xs">
			{INTENSITY_LABELS[cfg.intensity as Intensity] ?? cfg.intensity}
		</span>
		{#if stages.length}
			<span class="text-xs text-muted-foreground">{stages.length} stages</span>
		{/if}
	</div>
	<dl class="grid grid-cols-1 gap-x-8 gap-y-2 px-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
		{#each facts as [k, v] (k)}
			<div
				class="flex min-w-0 items-baseline justify-between gap-3 border-b border-border/40 pb-1.5"
			>
				<dt class="shrink-0 text-xs text-muted-foreground">{k}</dt>
				<dd class="truncate text-right">{v}</dd>
			</div>
		{/each}
	</dl>
	{#if stages.length}
		<div class="flex flex-wrap gap-1 px-1">
			{#each stages as s (s.name)}
				<span class="rounded border border-border/70 px-1.5 py-0.5 text-2xs text-muted-foreground"
					>{s.title}</span
				>
			{/each}
		</div>
	{/if}
</div>
