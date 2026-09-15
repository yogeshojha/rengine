<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import {
		CHECK_BY_KEY,
		FACT_CHIP,
		POSTURE_ANY,
		TONE_DOT,
		hostRows,
		postureQuery,
		share,
		sortChecks,
		zoneFacts
	} from '$lib/config/domain-posture';
	import type { DomainPostureSummary } from '$lib/types/domain-posture';
	import type { HygieneSummary } from '$lib/utilities/scan-insights';

	interface Props {
		summary: DomainPostureSummary | null;
		hosts: HygieneSummary | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { summary, hosts, scanId = null, loading = false, class: className = '' }: Props = $props();

	const TOP = 7;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const link = (query: string) => ROUTES.results(WEB.tab, scanId, { [WEB.queryParam]: query });

	let zone = $derived(summary && summary.zones.length === 1 ? summary.zones[0] : null);
	let issues = $derived(zone ? sortChecks(zone.posture_issues) : []);
	let facts = $derived(zone ? zoneFacts(zone) : []);
	let rows = $derived(
		hostRows(hosts)
			.map((r) => ({ ...r, share: Math.round(share(r)), href: link(r.query) }))
			.sort((a, b) => b.share - a.share || b.failing - a.failing)
			.slice(0, TOP)
	);
</script>

<Cell
	id="domain-posture"
	title="Domain posture"
	description="Checks per registrable domain"
	href={link(postureQuery(POSTURE_ANY))}
	hrefLabel={postureQuery(POSTURE_ANY)}
	loading={loading && !summary}
	class={className}
>
	{#if zone}
		<div class="flex flex-wrap gap-1">
			{#each facts as f (f.key)}
				<Hint text={f.hint}>
					{#snippet child(props)}
						<span
							{...props}
							class="inline-flex h-5 items-center gap-1 rounded-sm border px-1.5 text-2xs {FACT_CHIP[
								f.tone
							]}"
						>
							<span class="opacity-70">{f.label}</span>
							<span class="font-mono">{f.value}</span>
						</span>
					{/snippet}
				</Hint>
			{/each}
		</div>
		{#if issues.length}
			<ul class="flex flex-col divide-y divide-border/60">
				{#each issues as key (key)}
					{@const spec = CHECK_BY_KEY[key]}
					{@const evidence = zone.evidence[key]}
					<li class="flex items-start gap-2 py-1.5">
						<span class="flex h-5 shrink-0 items-center">
							<span
								class="size-1.5 rounded-full {spec ? TONE_DOT[spec.tone] : 'bg-muted'}"
								aria-hidden="true"
							></span>
						</span>
						<div class="min-w-0 flex-1">
							<Hint text={spec?.help}>
								{#snippet child(props)}
									<a
										{...props}
										href={link(postureQuery(key))}
										class="block text-sm leading-5 hover:underline">{spec?.label ?? key}</a
									>
								{/snippet}
							</Hint>
							{#if evidence}
								<p class="font-mono text-2xs break-all text-muted-foreground">{evidence}</p>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{:else}
			<span class="text-sm text-muted-foreground">Passes every applicable check</span>
		{/if}
	{:else if rows.length}
		<ul class="flex flex-col gap-1.5">
			{#each rows as r (r.spec.key)}
				<li>
					<a
						href={r.href}
						class="grid grid-cols-[7.5rem_1fr_2.75rem] items-center gap-2.5 text-xs hover:text-foreground"
					>
						<span class="truncate text-muted-foreground">{r.spec.label}</span>
						<span class="h-1.5 overflow-hidden rounded-full bg-muted">
							<span
								class="block h-full rounded-full {TONE_DOT[r.spec.tone]}"
								style="width:{r.share}%"
							></span>
						</span>
						<span class="text-right font-medium tabular-nums">{r.failing.toLocaleString()}</span>
					</a>
				</li>
			{/each}
		</ul>
	{:else}
		<span class="text-sm text-muted-foreground">No failing check</span>
	{/if}
	{#snippet footer()}
		{#if zone}
			<span class="font-mono">{zone.zone}</span>
			<span>{plural(zone.hosts, 'web asset', 'web assets')}</span>
		{:else if summary}
			<span>
				{plural(summary.zone_count, 'zone', 'zones')}{#if summary.mail_hosts}
					· {plural(summary.mail_hosts, 'mail host', 'mail hosts')}{/if}{#if summary.spoofable}
					· {summary.spoofable.toLocaleString()} spoofable{/if}
			</span>
			{#if hosts}
				<span class="tabular-nums">{plural(hosts.evaluated, 'web asset', 'web assets')}</span>
			{/if}
		{/if}
	{/snippet}
</Cell>
