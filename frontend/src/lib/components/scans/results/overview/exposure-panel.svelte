<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CompositionBar from './composition-bar.svelte';
	import type { Segment } from './composition-bar.svelte';
	import RankedList from './ranked-list.svelte';
	import type { RankedRow } from './ranked-list.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { SERVICE_CLASS_FILL, ServiceClass } from '$lib/config/service-classes';
	import type { ScanExposure } from '$lib/utilities/services';

	interface Props {
		exposure: ScanExposure | null;
		loading: boolean;
		onTab: (tab: string, filter?: string) => void;
	}

	let { exposure, loading, onTab }: Props = $props();

	const TOP = 5;
	const NON_WEB_FILTER = `not class:${ServiceClass.WEB}`;
	const SENSITIVE_FILTER = 'is:sensitive';
	const PASSIVE_FILTER = 'is:passive';
	const NONSTANDARD_FILTER = 'is:http and not port:[80,443]';
	const QUIET_FILTER = `class:${ServiceClass.WEB} and not is:http`;

	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	function pick(filter: string) {
		onTab('services', filter);
	}

	let bands = $derived.by<Segment[]>(() =>
		(exposure?.bands ?? [])
			.filter((b) => b.count > 0)
			.map((b) => ({
				key: b.key,
				label: b.label,
				count: b.count,
				color: SERVICE_CLASS_FILL[b.key] ?? SERVICE_CLASS_FILL[ServiceClass.OTHER],
				filter: b.query
			}))
	);

	let services = $derived.by<RankedRow[]>(() =>
		(exposure?.top_services ?? []).slice(0, TOP).map((s) => ({
			key: s.key,
			label: s.label,
			sub: s.detail ?? undefined,
			count: s.count,
			filter: s.query
		}))
	);

	let coverage = $derived.by<RankedRow[]>(() =>
		(exposure?.coverage ?? []).slice(0, TOP).map((c) => ({
			key: c.key,
			label: c.label,
			sub: c.detail ?? undefined,
			count: c.count,
			filter: c.query || undefined
		}))
	);

	let hasData = $derived(!!exposure && exposure.services > 0);
	let unconfirmed = $derived(exposure?.passive_only ?? 0);

	interface Headline {
		value: number;
		text: string;
	}

	// lead with the finding, not the total: the tail is what a review misses
	let headline = $derived.by<Headline | null>(() => {
		if (!exposure) return null;
		if (exposure.sensitive > 0)
			return {
				value: exposure.sensitive,
				text: `administrative or datastore ${exposure.sensitive === 1 ? 'port' : 'ports'} exposed`
			};
		if (exposure.non_web_services > 0)
			return {
				value: exposure.non_web_services,
				text: `${exposure.non_web_services === 1 ? 'service' : 'services'} outside the web surface`
			};
		if (exposure.nonstandard_web > 0)
			return {
				value: exposure.nonstandard_web,
				text: `web ${exposure.nonstandard_web === 1 ? 'service' : 'services'} on non-standard ports`
			};
		return {
			value: exposure.services,
			text: `${exposure.services === 1 ? 'service' : 'services'} listening across ${plural(exposure.addresses, 'address', 'addresses')}`
		};
	});
	let coverageBase = $derived(
		(exposure?.coverage ?? []).reduce((n, c) => n + c.count, 0) || (exposure?.addresses ?? 0)
	);
</script>

{#if loading && !exposure}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Exposure" />
		<div class="-mt-px -ml-px grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="flex flex-col gap-4 border-t border-l p-5">
					<Skeleton class="h-4 w-32" />
					<Skeleton class="h-1.5 w-full" />
					<Skeleton class="h-16 w-full" />
				</div>
			{/each}
		</div>
	</Card.Root>
{:else if hasData && exposure}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Exposure" description="Listening services and the evidence for each">
			<span class="tabular-nums">
				{plural(exposure.services, 'service', 'services')} · {plural(
					exposure.addresses,
					'address',
					'addresses'
				)}
			</span>
		</PanelHead>

		<div class="flex flex-wrap items-center gap-x-6 gap-y-3 border-b px-5 py-4">
			{#if headline}
				{@const h = headline}
				<div class="flex min-w-0 items-baseline gap-2">
					<span class="text-2xl leading-8 font-semibold tabular-nums">
						{h.value.toLocaleString()}
					</span>
					<span class="text-sm text-muted-foreground">{h.text}</span>
				</div>
			{/if}
			<div class="flex flex-wrap items-center gap-2">
				{#if exposure.sensitive > 0}
					<Button
						variant="outline"
						size="sm"
						class="h-8 gap-1.5 border-warning/40 text-warning hover:bg-warning/10 hover:text-warning"
						onclick={() => pick(SENSITIVE_FILTER)}
					>
						{plural(exposure.sensitive, 'sensitive port', 'sensitive ports')}
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
				{#if exposure.non_web_services > 0}
					<Button
						variant="outline"
						size="sm"
						class="h-8 gap-1.5"
						onclick={() => pick(NON_WEB_FILTER)}
					>
						{plural(exposure.non_web_services, 'non-web service', 'non-web services')}
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
				{#if exposure.nonstandard_web > 0}
					<Button
						variant="outline"
						size="sm"
						class="h-8 gap-1.5"
						onclick={() => pick(NONSTANDARD_FILTER)}
					>
						{plural(exposure.nonstandard_web, 'web service', 'web services')} on non-standard ports
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
			</div>
		</div>

		<div
			class="-mt-px -ml-px grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(15rem,1fr))]"
		>
			<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
				<div class="flex flex-col gap-0.5">
					<h3 class="text-sm font-medium">Service classes</h3>
					<p class="text-xs text-muted-foreground">
						{exposure.answering_http.toLocaleString()} of {exposure.services.toLocaleString()} answered
						an HTTP request
					</p>
				</div>
				<CompositionBar
					segments={bands}
					total={exposure.services}
					label="Services by class"
					onSelect={pick}
				/>
				{#if exposure.web_services > exposure.answering_http}
					<Button
						variant="link"
						size="sm"
						class="mt-auto h-auto gap-1 self-start px-0 text-xs"
						onclick={() => pick(QUIET_FILTER)}
					>
						{plural(exposure.web_services - exposure.answering_http, 'web port', 'web ports')} with no
						HTTP response
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
			</section>

			{#if services.length}
				<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
					<div class="flex items-baseline justify-between gap-3">
						<h3 class="text-sm font-medium">Top services</h3>
						{#if exposure.named > 0}
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
								{exposure.named.toLocaleString()} identified
							</span>
						{/if}
					</div>
					<RankedList rows={services} base={exposure.services} onSelect={pick}>
						{#snippet icon(r)}
							<TechIcon name={r.label} class="size-4" />
						{/snippet}
					</RankedList>
					<Button
						variant="link"
						size="sm"
						class="mt-auto h-auto gap-1 self-start px-0 text-xs"
						onclick={() => onTab('services')}
					>
						View all services
						<ChevronRight class="size-3.5" />
					</Button>
				</section>
			{/if}

			{#if coverage.length}
				<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
					<div class="flex flex-col gap-0.5">
						<h3 class="text-sm font-medium">Scan coverage</h3>
						<p class="text-xs text-muted-foreground">Port scan reach per address</p>
					</div>
					<RankedList rows={coverage} base={coverageBase} onSelect={pick} />
					{#if unconfirmed > 0}
						<Button
							variant="link"
							size="sm"
							class="mt-auto h-auto gap-1 self-start px-0 text-xs"
							onclick={() => pick(PASSIVE_FILTER)}
						>
							{plural(unconfirmed, 'port', 'ports')} reported by external scanners, not confirmed
							<ChevronRight class="size-3.5" />
						</Button>
					{/if}
				</section>
			{/if}
		</div>
	</Card.Root>
{/if}
