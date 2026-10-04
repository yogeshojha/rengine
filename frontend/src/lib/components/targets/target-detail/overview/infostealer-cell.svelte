<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import {
		AUDIENCE,
		AUDIENCE_ORDER,
		Audience,
		SOURCE_NAME,
		STANDING
	} from '$lib/config/infostealer';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { InfostealerReport } from '$lib/types/infostealer';
	import { formatDateTime, relativeTimeLong } from '$lib/utilities/dates';
	import { safeHref } from '$lib/utilities/links';

	interface Props {
		targetId: string;
		report: InfostealerReport;
		class?: string;
	}

	let { targetId, report, class: className = '' }: Props = $props();

	const TOP = 4;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	let counts = $derived(
		AUDIENCE_ORDER.map((a) => ({
			key: a,
			...AUDIENCE[a],
			value: a === Audience.EMPLOYEE ? report.employees : report.users
		}))
	);
	let top = $derived(
		report.hosts
			.filter((h) => h.employee_credentials > 0)
			.slice(0, TOP)
			.map((h) => ({ host: h.host, count: h.employee_credentials, standing: STANDING[h.standing] }))
	);
	let inScanHref = $derived(
		report.scan_id && report.in_scan > 0
			? ROUTES.scanTab(report.scan_id, WEB.tab, { [WEB.queryParam]: report.query })
			: null
	);
</script>

<Cell
	id="infostealer"
	title="Infostealer infections"
	href={ROUTES.target(targetId, 'infostealer')}
	class={className}
>
	<div class="grid grid-cols-2 gap-3">
		{#each counts as c (c.key)}
			<div class="flex flex-col gap-1">
				<span
					class="flex items-center gap-1.5 text-2xs tracking-wide text-muted-foreground uppercase"
				>
					<c.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
					{c.label}
				</span>
				<span class="text-lg leading-7 font-semibold tabular-nums">{c.value.toLocaleString()}</span>
			</div>
		{/each}
	</div>
	{#if report.last_employee_at}
		<Hint text={formatDateTime(report.last_employee_at)}>
			{#snippet child(props)}
				<span {...props} class="w-fit text-xs text-muted-foreground">
					Last employee infection {relativeTimeLong(report.last_employee_at)}
				</span>
			{/snippet}
		</Hint>
	{/if}
	{#if top.length}
		<ul class="flex flex-col gap-1 border-t pt-2.5">
			{#each top as t (t.host)}
				<li class="flex items-center gap-2 text-xs">
					<Hint text={t.standing.label}>
						{#snippet child(props)}
							<span {...props} class="flex h-4 shrink-0 items-center {t.standing.tone}">
								<t.standing.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
							</span>
						{/snippet}
					</Hint>
					<span class="min-w-0 flex-1 truncate font-mono">{t.host}</span>
					<span class="shrink-0 font-medium tabular-nums">{t.count.toLocaleString()}</span>
				</li>
			{/each}
		</ul>
	{/if}
	{#snippet footer()}
		{#if inScanHref}
			<a href={safeHref(inScanHref)} class="hover:text-foreground">
				{report.in_scan} of {report.host_count} hostnames in scan
			</a>
		{:else}
			<span>{report.host_count.toLocaleString()} hostnames</span>
		{/if}
		<span>{SOURCE_NAME}</span>
	{/snippet}
</Cell>
