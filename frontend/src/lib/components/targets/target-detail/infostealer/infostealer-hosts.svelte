<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import { SvelteSet } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui/button';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { AUDIENCE, HostStanding, STANDING, hostQuery, loginLabel } from '$lib/config/infostealer';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { InfostealerHost, InfostealerReport } from '$lib/types/infostealer';
	import { safeHref } from '$lib/utilities/links';

	interface Props {
		report: InfostealerReport;
	}

	let { report }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const GRID =
		'grid grid-cols-[minmax(0,1fr)_4.5rem_4.5rem_1.75rem] items-center gap-x-3 sm:grid-cols-[minmax(0,1fr)_6rem_6rem_9rem]';
	const open = new SvelteSet<string>();

	const webAssets = (query: string) =>
		report.scan_id ? ROUTES.scanTab(report.scan_id, WEB.tab, { [WEB.queryParam]: query }) : null;
	const hostHref = (h: InfostealerHost) =>
		h.standing === HostStanding.ABSENT ? null : webAssets(hostQuery(h.host));

	function toggle(host: string) {
		if (open.has(host)) open.delete(host);
		else open.add(host);
	}

	let inScanHref = $derived(webAssets(report.query));
</script>

<section class="overflow-hidden rounded-xl border bg-card">
	<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-1 px-4 pt-3.5 pb-3">
		<div class="flex flex-col gap-0.5">
			<SectionHead title="Logins" icon={KeyRound} count={report.hosts.length} />
			<p class="text-xs text-muted-foreground">Credentials per hostname, by audience</p>
		</div>
		{#if inScanHref && report.in_scan > 0}
			<a
				href={safeHref(inScanHref)}
				class="rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				<span class="font-medium text-foreground tabular-nums">{report.in_scan}</span>
				of {report.hosts.length} hostnames in scan
			</a>
		{/if}
	</div>

	<div
		aria-hidden="true"
		class="{GRID} border-y bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		<span>Host</span>
		<span class="text-right">Employees</span>
		<span class="text-right">Users</span>
		<span class="hidden sm:inline sm:pl-2">Scan</span>
	</div>
	<ul aria-label="Logins">
		{#each report.hosts as h (h.host)}
			{@const standing = STANDING[h.standing]}
			{@const href = hostHref(h)}
			{@const expanded = open.has(h.host)}
			<li class="border-b last:border-b-0">
				<div class="{GRID} group px-4 py-2 text-sm">
					<span class="flex min-w-0 items-center gap-1.5">
						<Button
							variant="ghost"
							size="icon-xs"
							class="text-muted-foreground"
							aria-expanded={expanded}
							aria-label="{expanded ? 'Hide' : 'Show'} logins on {h.host}"
							onclick={() => toggle(h.host)}
						>
							<ChevronRight class="size-3.5 transition-transform {expanded ? 'rotate-90' : ''}" />
						</Button>
						{#if href}
							<a
								href={safeHref(href)}
								class="min-w-0 font-mono text-xs wrap-anywhere hover:text-primary"
							>
								{h.host}
							</a>
						{:else}
							<span class="min-w-0 font-mono text-xs wrap-anywhere">{h.host}</span>
						{/if}
						<span
							class="flex h-5 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:focus-within:opacity-100"
						>
							<CopyButton value={h.host} label="Copy host" />
						</span>
					</span>
					<span
						class="text-right text-xs tabular-nums {h.employee_credentials
							? 'font-medium'
							: 'text-muted-foreground/50'}"
					>
						{h.employee_credentials.toLocaleString()}
					</span>
					<span
						class="text-right text-xs tabular-nums {h.user_credentials
							? ''
							: 'text-muted-foreground/50'}"
					>
						{h.user_credentials.toLocaleString()}
					</span>
					<span class="flex min-w-0 items-center gap-1.5 text-xs sm:pl-2 {standing.tone}">
						<Hint text={standing.label}>
							{#snippet child(props)}
								<span {...props} class="flex h-5 shrink-0 items-center">
									<standing.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
								</span>
							{/snippet}
						</Hint>
						<span class="hidden truncate sm:inline">{standing.label}</span>
					</span>
				</div>

				{#if expanded}
					<ul class="flex flex-col gap-0.5 bg-muted/20 px-4 pt-1 pb-2.5 pl-10">
						{#each h.paths as p, i (i)}
							{@const audience = AUDIENCE[p.audience]}
							<li class="flex items-center gap-2 text-xs">
								<Hint text={audience.label}>
									{#snippet child(props)}
										<span {...props} class="flex h-5 shrink-0 items-center text-muted-foreground">
											<audience.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
										</span>
									{/snippet}
								</Hint>
								<span class="min-w-0 flex-1 font-mono text-2xs wrap-anywhere text-muted-foreground">
									{loginLabel(h.host, p)}
								</span>
								<span class="shrink-0 tabular-nums">{p.credentials.toLocaleString()}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</li>
		{/each}
	</ul>
</section>
