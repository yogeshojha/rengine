<script lang="ts">
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
	import { ENDPOINT_CLASS_FILL, EndpointClass } from '$lib/config/endpoints';
	import type { ScanStructure } from '$lib/utilities/endpoints';

	interface Props {
		structure: ScanStructure | null;
		loading: boolean;
		onTab: (tab: string, filter?: string) => void;
	}

	let { structure, loading, onTab }: Props = $props();

	const TOP = 5;
	const FINDING_ICON = {
		auth_boundary: DoorOpen,
		exposed_file: ShieldAlert,
		archive_only: Archive
	} as const;

	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	function pick(filter: string) {
		onTab('endpoints', filter);
	}

	let hasData = $derived(!!structure && structure.endpoints > 0);
	let unverified = $derived(Math.max(0, (structure?.endpoints ?? 0) - (structure?.probed ?? 0)));

	let classes = $derived.by<Segment[]>(() =>
		(structure?.by_class ?? [])
			.filter((c) => c.count > 0)
			.map((c) => ({
				key: c.key,
				label: c.label,
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
			sub: `on ${plural(p.hosts, 'host', 'hosts')}`,
			count: p.hosts,
			filter: p.query
		}))
	);

	let interest = $derived.by<RankedRow[]>(() =>
		(structure?.interest ?? []).slice(0, TOP).map((i) => ({
			key: i.key,
			label: i.label,
			sub: i.hosts ? `on ${plural(i.hosts, 'host', 'hosts')}` : undefined,
			count: i.count,
			filter: i.query
		}))
	);

	let sharedBase = $derived(structure?.hosts ?? 0);
	let interestBase = $derived(structure?.endpoints ?? 0);
	let findings = $derived((structure?.findings ?? []).slice(0, 4));
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
			<div class="ml-auto flex flex-wrap items-center gap-2">
				{#if structure.with_params && !structure.headline?.endsWith('accept input')}
					<Button
						variant="outline"
						size="sm"
						class="h-7 gap-1.5 text-xs"
						onclick={() => pick('is:param')}
					>
						{plural(structure.with_params, 'endpoint takes', 'endpoints take')} input
					</Button>
				{/if}
				{#if unverified}
					<Button
						variant="outline"
						size="sm"
						class="h-7 gap-1.5 text-xs"
						onclick={() => pick('not is:probed')}
					>
						{unverified.toLocaleString()} not checked
					</Button>
				{/if}
			</div>
		</div>

		<div class="-mt-px -ml-px grid grid-cols-1 md:grid-cols-[repeat(auto-fit,minmax(18rem,1fr))]">
			{#if findings.length}
				<div class="flex flex-col gap-3 border-t border-l p-5">
					<h3 class="text-xs font-medium text-muted-foreground uppercase">Worth a look</h3>
					<ul class="space-y-2.5">
						{#each findings as f (f.kind + f.label)}
							{@const Icon = FINDING_ICON[f.kind as keyof typeof FINDING_ICON] ?? ShieldAlert}
							<li>
								<button
									type="button"
									class="group flex w-full gap-2 text-left"
									onclick={() => pick(f.query)}
								>
									<span
										class="flex h-5 shrink-0 items-center {f.kind === 'exposed_file'
											? 'text-destructive'
											: 'text-warning'}"
									>
										<Icon class="size-3.5" />
									</span>
									<span class="min-w-0 flex-1">
										<span class="block truncate font-mono text-xs group-hover:text-primary">
											{f.label}
										</span>
										<span class="block text-xs text-muted-foreground">{f.detail}</span>
									</span>
									<ChevronRight
										class="mt-0.5 size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
									/>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if shared.length}
				<div class="flex flex-col gap-3 border-t border-l p-5">
					<h3 class="text-xs font-medium text-muted-foreground uppercase">Shared across hosts</h3>
					<p class="text-xs text-muted-foreground">
						The same route on many hosts is one piece of software. A single change resolves every
						instance.
					</p>
					<RankedList rows={shared} base={sharedBase} onSelect={pick} />
				</div>
			{/if}

			<div class="flex flex-col gap-3 border-t border-l p-5">
				<h3 class="text-xs font-medium text-muted-foreground uppercase">Endpoint kinds</h3>
				<CompositionBar
					segments={classes}
					total={structure.endpoints}
					label="endpoints by kind"
					onSelect={pick}
				/>
			</div>

			{#if interest.length}
				<div class="flex flex-col gap-3 border-t border-l p-5">
					<h3 class="text-xs font-medium text-muted-foreground uppercase">Of interest</h3>
					<RankedList rows={interest} base={interestBase} onSelect={pick} />
				</div>
			{/if}
		</div>
	</Card.Root>
{/if}
