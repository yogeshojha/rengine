<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CompositionBar, {
		type Segment
	} from '$lib/components/scans/results/overview/composition-bar.svelte';
	import RankedList, {
		type RankedRow
	} from '$lib/components/scans/results/overview/ranked-list.svelte';
	import ServiceIcon from '$lib/components/scans/results/services/service-icon.svelte';
	import SignalSheet, { type SheetRow } from './signal-sheet.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		SERVICE_CLASS_FILL,
		SERVICE_CLASS_LABELS,
		ServiceClass
	} from '$lib/config/service-classes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type {
		DashboardExposedService,
		DashboardExposure,
		DashboardTargetCount
	} from '$lib/types/dashboard';

	interface Props {
		exposure: DashboardExposure;
		sensitive: DashboardTargetCount[];
	}

	let { exposure, sensitive }: Props = $props();

	const TOP_TARGETS = 5;
	const SENSITIVE_QUERY = 'is:sensitive';
	const SERVICES = SURFACE[SurfaceDimension.SERVICES];
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const targets = (n: number) => plural(n, 'target', 'targets');

	let bands = $derived<Segment[]>(
		exposure.bands.map((b) => ({
			key: b.key,
			label: b.label,
			count: b.count,
			color: SERVICE_CLASS_FILL[b.key] ?? SERVICE_CLASS_FILL[ServiceClass.OTHER]
		}))
	);
	let byKey = $derived(new Map(exposure.top.map((s) => [s.key, s])));
	let rows = $derived<RankedRow[]>(
		exposure.top.map((s) => ({
			key: s.key,
			label: s.label,
			sub: `${SERVICE_CLASS_LABELS[s.service_class] ?? s.service_class} · on ${targets(s.targets.length)}`,
			badge: s.sensitive ? 'sensitive' : undefined,
			count: s.count,
			filter: s.key
		}))
	);
	let concentration = $derived(sensitive.slice(0, TOP_TARGETS));
	let maxSensitive = $derived(Math.max(1, ...concentration.map((t) => t.count)));

	interface Headline {
		value: number;
		text: string;
	}
	let headline = $derived.by<Headline>(() => {
		if (exposure.sensitive > 0)
			return {
				value: exposure.sensitive,
				text: `administrative or datastore ${exposure.sensitive === 1 ? 'port' : 'ports'} exposed across ${targets(exposure.sensitive_targets)}`
			};
		if (exposure.non_web > 0)
			return {
				value: exposure.non_web,
				text: `${exposure.non_web === 1 ? 'service' : 'services'} outside the web surface`
			};
		return {
			value: exposure.services,
			text: `${exposure.services === 1 ? 'service' : 'services'} listening across ${plural(exposure.addresses, 'address', 'addresses')}`
		};
	});

	let picked = $state<DashboardExposedService | null>(null);
	let sheetOpen = $state(false);
	let sheetRows = $derived<SheetRow[]>(
		(picked?.targets ?? []).map((t) => ({
			key: t.target_id,
			primary: t.target_value,
			meta: plural(t.count, 'service', 'services'),
			href: ROUTES.scanTab(t.scan_id, SERVICES.tab, {
				[SERVICES.queryParam]: picked?.query ?? ''
			})
		}))
	);
	function pick(key: string) {
		const s = byKey.get(key);
		if (!s) return;
		picked = s;
		sheetOpen = true;
	}
</script>

{#if exposure.services > 0}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Exposure">
			<span class="tabular-nums">
				{plural(exposure.services, 'service', 'services')} · {plural(
					exposure.addresses,
					'address',
					'addresses'
				)} · {exposure.targets} scanned {exposure.targets === 1 ? 'target' : 'targets'}
			</span>
		</PanelHead>

		<div class="flex flex-wrap items-baseline gap-x-2 border-b px-5 py-4">
			<span class="text-2xl leading-8 font-semibold tabular-nums">
				{headline.value.toLocaleString()}
			</span>
			<span class="text-sm text-muted-foreground">{headline.text}</span>
		</div>

		<div class="-mt-px -ml-px grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
			<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
				<div class="flex flex-col gap-0.5">
					<h3 class="text-sm font-medium">What is listening</h3>
					<p class="text-xs text-muted-foreground">
						Every open port on the latest service scan of each target, by class
					</p>
				</div>
				<CompositionBar segments={bands} total={exposure.services} label="Services by class" />
				{#if concentration.length}
					<div class="mt-auto flex flex-col gap-3 border-t pt-4">
						<div class="flex flex-col gap-0.5">
							<h3 class="text-sm font-medium">Where it concentrates</h3>
							<p class="text-xs text-muted-foreground">
								Sensitive ports per target, from its latest service scan
							</p>
						</div>
						<ul class="flex flex-col gap-2.5">
							{#each concentration as t (t.target_id)}
								<li>
									<a
										href={ROUTES.scanTab(t.scan_id, SERVICES.tab, {
											[SERVICES.queryParam]: SENSITIVE_QUERY
										})}
										class="flex w-full flex-col gap-1 text-left hover:opacity-80"
									>
										<span class="flex items-baseline justify-between gap-3">
											<span class="min-w-0 truncate font-mono text-xs">{t.target_value}</span>
											<span class="shrink-0 text-xs font-medium tabular-nums">
												{t.count.toLocaleString()}
											</span>
										</span>
										<span class="flex h-1 w-full overflow-hidden rounded-full bg-muted">
											<span
												class="h-full rounded-full bg-warning"
												style="width:{(t.count / maxSensitive) * 100}%"
											></span>
										</span>
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
				<div class="flex flex-col gap-0.5">
					<h3 class="text-sm font-medium">Most exposed services</h3>
					<p class="text-xs text-muted-foreground">
						Non-web services ranked by reach, sensitive ones first
					</p>
				</div>
				<RankedList {rows} base={exposure.non_web} onSelect={pick}>
					{#snippet icon(r)}
						{@const s = byKey.get(r.key)}
						<ServiceIcon
							service={r.key}
							serviceClass={s?.service_class ?? ServiceClass.OTHER}
							class="size-4"
						/>
					{/snippet}
				</RankedList>
			</section>
		</div>
	</Card.Root>
{/if}

{#if picked}
	<SignalSheet
		open={sheetOpen}
		onOpenChange={(v) => (sheetOpen = v)}
		title="{picked.label} by target"
		description="Where {picked.label} is listening, from each target's latest service scan"
		rows={sheetRows}
	/>
{/if}
