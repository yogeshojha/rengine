<script lang="ts">
	import AppWindow from '@lucide/svelte/icons/app-window';
	import Bug from '@lucide/svelte/icons/bug';
	import LockKeyhole from '@lucide/svelte/icons/lock-keyhole';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import RankedBars, { type BarRow } from '$lib/components/dashboard/ranked-bars.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { AUDIENCE, AUDIENCE_ORDER, STRENGTH, STRENGTH_ORDER } from '$lib/config/infostealer';
	import type { InfostealerReport, NamedCount } from '$lib/types/infostealer';

	interface Props {
		report: InfostealerReport;
	}

	let { report }: Props = $props();

	const FAMILIES = 8;
	const SERVICES = 10;

	const bars = (rows: NamedCount[], limit: number): BarRow[] =>
		rows
			.filter((r) => (r.count ?? 0) > 0)
			.slice(0, limit)
			.map((r) => ({ key: r.name, label: r.name, count: r.count ?? 0 }));

	let families = $derived(bars(report.families, FAMILIES));
	let services = $derived(bars(report.services, SERVICES));
	let strength = $derived(
		AUDIENCE_ORDER.flatMap((audience) => {
			const buckets = report.passwords[audience];
			if (!buckets) return [];
			const total = STRENGTH_ORDER.reduce((n, s) => n + (buckets[s] ?? 0), 0);
			if (!total) return [];
			return [
				{
					audience,
					total,
					parts: STRENGTH_ORDER.map((s) => ({
						key: s,
						count: buckets[s] ?? 0,
						share: ((buckets[s] ?? 0) / total) * 100
					}))
				}
			];
		})
	);
	let shown = $derived(
		[families.length, strength.length, report.applications.length, services.length].filter(Boolean)
			.length
	);
</script>

{#if shown}
	<div class="grid gap-4 {shown > 1 ? 'lg:grid-cols-2' : ''}">
		{#if families.length}
			<section class="flex flex-col gap-3 rounded-xl border bg-card px-4 py-3.5">
				<SectionHead title="Stealer families" icon={Bug} />
				<RankedBars rows={families} />
			</section>
		{/if}

		{#if strength.length}
			<section class="flex flex-col gap-3 rounded-xl border bg-card px-4 py-3.5">
				<SectionHead title="Password strength" icon={LockKeyhole} />
				<div class="flex flex-col gap-3.5">
					{#each strength as row (row.audience)}
						<div class="flex flex-col gap-1.5">
							<div class="flex items-baseline justify-between gap-3 text-sm">
								<span>{AUDIENCE[row.audience].label}</span>
								<span class="text-xs text-muted-foreground tabular-nums">
									{row.total.toLocaleString()} passwords
								</span>
							</div>
							<div class="flex h-2 w-full overflow-hidden rounded-full bg-muted">
								{#each row.parts as part (part.key)}
									{#if part.count}
										<span class="h-full {STRENGTH[part.key].fill}" style="width:{part.share}%"
										></span>
									{/if}
								{/each}
							</div>
							<ul class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
								{#each row.parts as part (part.key)}
									<li class="flex items-center gap-1.5">
										<span class="size-2 rounded-full {STRENGTH[part.key].fill}"></span>
										{STRENGTH[part.key].label}
										<span class="text-foreground/80 tabular-nums">{Math.round(part.share)}%</span>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		{#if report.applications.length}
			<section class="flex flex-col gap-3 rounded-xl border bg-card px-4 py-3.5">
				<SectionHead title="Applications" icon={AppWindow} count={report.applications.length} />
				<div class="flex flex-wrap gap-1.5">
					{#each report.applications as app (app.name)}
						<span
							class="inline-flex h-6 items-center gap-1.5 rounded-md border bg-muted/30 px-2 text-xs"
						>
							<span class="font-mono">{app.name}</span>
							{#if app.count != null}
								<span class="text-muted-foreground tabular-nums">{app.count.toLocaleString()}</span>
							{/if}
						</span>
					{/each}
				</div>
			</section>
		{/if}

		{#if services.length}
			<section class="flex flex-col gap-3 rounded-xl border bg-card px-4 py-3.5">
				<SectionHead title="Third-party services" icon={Waypoints} />
				<RankedBars rows={services} />
			</section>
		{/if}
	</div>
{/if}
