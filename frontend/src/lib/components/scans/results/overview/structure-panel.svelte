<script lang="ts">
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Archive from '@lucide/svelte/icons/archive';
	import DoorOpen from '@lucide/svelte/icons/door-open';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CompositionBar from './composition-bar.svelte';
	import type { Segment } from './composition-bar.svelte';
	import RankedList from './ranked-list.svelte';
	import type { RankedRow } from './ranked-list.svelte';
	import {
		ENDPOINT_CLASS_FILL,
		ENDPOINT_CLASS_LABELS,
		EndpointClass,
		INTEREST_LABELS
	} from '$lib/config/endpoints';
	import type { ScanStructure } from '$lib/utilities/endpoints';
	import { plural } from '$lib/utilities/strings';

	interface Props {
		structure: ScanStructure | null;
		loading: boolean;
		onTab: (tab: ResultTab, filter?: string) => void;
	}

	let { structure, loading, onTab }: Props = $props();

	const EP = SURFACE[SurfaceDimension.ENDPOINTS];

	const TOP = 5;
	const FINDING_ICON = {
		auth_boundary: DoorOpen,
		exposed_file: ShieldAlert,
		archive_only: Archive
	} as const;

	const sentence = (s: string) => {
		const text = s.replace(/[_-]+/g, ' ').trim();
		return text.charAt(0).toUpperCase() + text.slice(1);
	};

	function pick(filter: string) {
		onTab(EP.tab, filter);
	}

	let hasData = $derived(!!structure && structure.endpoints > 0);
	let unverified = $derived(Math.max(0, (structure?.endpoints ?? 0) - (structure?.probed ?? 0)));

	let classes = $derived.by<Segment[]>(() =>
		(structure?.by_class ?? [])
			.filter((c) => c.count > 0)
			.map((c) => ({
				key: c.key,
				label: ENDPOINT_CLASS_LABELS[c.key] ?? sentence(c.label),
				count: c.count,
				color: ENDPOINT_CLASS_FILL[c.key] ?? ENDPOINT_CLASS_FILL[EndpointClass.OTHER],
				filter: c.query
			}))
	);

	let shared = $derived.by<RankedRow[]>(() =>
		(structure?.shared_paths ?? []).slice(0, TOP).map((p) => ({
			key: p.path,
			label: p.path,
			mono: true,
			sub: `on ${plural(p.hosts, 'web asset', 'web assets')}`,
			count: p.hosts,
			filter: p.query
		}))
	);

	let interest = $derived.by<RankedRow[]>(() =>
		(structure?.interest ?? []).slice(0, TOP).map((i) => ({
			key: i.key,
			label: INTEREST_LABELS[i.key] ?? sentence(i.label),
			sub: i.hosts ? `on ${plural(i.hosts, 'web asset', 'web assets')}` : undefined,
			count: i.count,
			filter: i.query
		}))
	);

	let sharedBase = $derived(structure?.hosts ?? 0);
	let interestBase = $derived(structure?.endpoints ?? 0);
	let findings = $derived((structure?.findings ?? []).slice(0, 4));
	let sections = $derived(
		1 + (findings.length ? 1 : 0) + (shared.length ? 1 : 0) + (interest.length ? 1 : 0)
	);
	const GRID: Record<number, string> = {
		1: '',
		2: 'md:grid-cols-2',
		3: 'md:grid-cols-2 xl:grid-cols-3',
		4: 'md:grid-cols-2 2xl:grid-cols-4'
	};
</script>

{#if loading && !structure}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Site structure" />
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
{:else if hasData && structure}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Site structure">
			<span class="tabular-nums">
				{plural(structure.endpoints, 'endpoint', 'endpoints')} · {plural(
					structure.directories,
					'folder',
					'folders'
				)}
			</span>
		</PanelHead>

		<div class="flex flex-wrap items-center gap-x-6 gap-y-3 border-b px-5 py-4">
			{#if structure.headline}
				<p class="min-w-0 text-sm">{structure.headline}</p>
			{/if}
			<div class="flex flex-wrap items-center gap-2">
				{#if structure.with_params && (structure.findings.some((f) => f.kind === 'auth_boundary' || f.kind === 'exposed_file') || structure.shared_paths.length)}
					<Button variant="outline" size="sm" onclick={() => pick('is:param')}>
						{plural(structure.with_params, 'endpoint takes', 'endpoints take')} input
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
				{#if unverified}
					<Button variant="outline" size="sm" onclick={() => pick('not is:probed')}>
						{unverified.toLocaleString()} not checked
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
			</div>
		</div>

		<div class="-mt-px -ml-px grid grid-cols-1 {GRID[sections]}">
			{#if findings.length}
				<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
					<h3 class="text-sm font-semibold">Interest</h3>
					<ul class="-mx-2 flex flex-col gap-0.5">
						{#each findings as f (f.kind + f.label)}
							{@const Icon = FINDING_ICON[f.kind as keyof typeof FINDING_ICON] ?? ShieldAlert}
							<li>
								<button
									type="button"
									class="group flex w-full gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/50"
									onclick={() => pick(f.query)}
								>
									<span
										class="flex h-4 shrink-0 items-center {f.kind === 'exposed_file'
											? 'text-destructive'
											: 'text-warning'}"
									>
										<Icon class="size-3.5" />
									</span>
									<span class="min-w-0 flex-1">
										<span class="block truncate font-mono text-xs">{f.label}</span>
										<span class="block text-xs text-muted-foreground">{f.detail}</span>
									</span>
									<span class="flex h-4 shrink-0 items-center">
										<ChevronRight
											class="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
										/>
									</span>
								</button>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if shared.length}
				<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
					<h3 class="text-sm font-semibold">Shared across web assets</h3>
					<RankedList rows={shared} base={sharedBase} onSelect={pick} />
				</section>
			{/if}

			<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
				<h3 class="text-sm font-semibold">Endpoint kinds</h3>
				<CompositionBar
					segments={classes}
					total={structure.endpoints}
					label="endpoints by kind"
					onSelect={pick}
				/>
			</section>

			{#if interest.length}
				<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
					<h3 class="text-sm font-semibold">Path interests</h3>
					<RankedList rows={interest} base={interestBase} onSelect={pick} />
				</section>
			{/if}
		</div>
	</Card.Root>
{/if}
