<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Layers from '@lucide/svelte/icons/layers';
	import Boxes from '@lucide/svelte/icons/boxes';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import Network from '@lucide/svelte/icons/network';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import Heading from '@lucide/svelte/icons/heading';
	import Image from '@lucide/svelte/icons/image';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Flag from '@lucide/svelte/icons/flag';
	import Plug from '@lucide/svelte/icons/plug';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TechIcon from '../tech-icon.svelte';
	import CountryFlag from '../country-flag.svelte';
	import {
		providerFor,
		PROVIDER_KIND_ICONS,
		PROVIDER_KIND_LABELS
	} from '$lib/config/hosting-providers';
	import { httpStatusClass, isPrivateIp, STATUS_DOT } from '$lib/utilities/scan-correlation';
	import { productBrand } from '$lib/utilities/services';
	import { SERVICE_CLASS_ICONS } from '$lib/config/service-classes';
	import type { IconComponent } from '$lib/config/icons';
	import type { QueryGroup, QueryGroups, QueryGroupSpec } from '$lib/types/asset-query';

	interface Props {
		set: QueryGroups | null;
		dimensions: QueryGroupSpec[];
		noun: string;
		nounPlural: string;
		loading: boolean;
		onPick: (query: string) => void;
	}

	let { set, dimensions, noun, nounPlural, loading, onPick }: Props = $props();

	interface Identity {
		icon: IconComponent;
		logo: string | null;
		dot: string | null;
		note: string | null;
	}

	const MONO = new Set(['ip', 'favicon', 'cname', 'content_hash', 'jarm', 'prefix', 'port']);
	const ICONS: Record<string, IconComponent> = {
		tech: Boxes,
		cdn: Globe,
		server: Server,
		ip: Network,
		cname: Waypoints,
		title: Heading,
		favicon: Image,
		asn: Network,
		org: Building2,
		prefix: Network,
		country: Flag,
		port: Plug,
		service: Plug,
		product: Boxes,
		class: Layers,
		source: Fingerprint
	};
	const LOGO_DIMENSIONS = new Set(['tech', 'cdn', 'server', 'service', 'product']);

	function identify(dimension: string, group: QueryGroup): Identity {
		const base: Identity = { icon: ICONS[dimension] ?? Layers, logo: null, dot: null, note: null };
		if (dimension === 'class') {
			return { ...base, icon: SERVICE_CLASS_ICONS[group.value] ?? Layers };
		}
		if (LOGO_DIMENSIONS.has(dimension))
			return { ...base, logo: productBrand(group.label) || group.label };
		if (dimension === 'status') {
			return { ...base, dot: STATUS_DOT[httpStatusClass(Number.parseInt(group.value, 10) * 100)] };
		}
		if (dimension === 'cname') {
			const provider = providerFor(group.value);
			if (!provider) return base;
			return {
				icon: PROVIDER_KIND_ICONS[provider.kind],
				logo: provider.label,
				dot: null,
				note: `${provider.label} · ${PROVIDER_KIND_LABELS[provider.kind]}`
			};
		}
		if (dimension === 'ip') {
			if (isPrivateIp(group.value)) return { ...base, note: 'Private address' };
			if (group.value.includes(':')) return { ...base, note: 'IPv6' };
		}
		return base;
	}

	let dimension = $derived(set?.dimension ?? '');
	let groups = $derived(set?.groups ?? []);
	let spec = $derived(dimensions.find((d) => d.key === dimension));
	let label = $derived(spec?.label ?? 'value');
	let mono = $derived(MONO.has(dimension));
	let covered = $derived(set?.covered ?? 0);
	let rows = $derived(set?.rows ?? 0);
	let coverage = $derived(rows ? Math.round((covered / rows) * 100) : 0);
	let summary = $derived.by(() => {
		const n = set?.total_groups ?? 0;
		const base = `${n.toLocaleString()} ${n === 1 ? 'group' : 'groups'}`;
		return set?.truncated ? `${base} · showing ${groups.length}` : base;
	});

	function share(count: number): number {
		return covered ? (count / covered) * 100 : 0;
	}
	function shareLabel(count: number): string {
		const pct = share(count);
		return pct > 0 && pct < 1 ? '<1%' : `${Math.round(pct)}%`;
	}
</script>

{#if loading && groups.length === 0}
	<div class="flex items-center justify-between gap-6 border-b px-4 py-3">
		<div class="space-y-1.5">
			<Skeleton class="h-4 w-28" />
			<Skeleton class="h-3 w-48" />
		</div>
		<Skeleton class="h-3 w-40" />
	</div>
	<div class="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
		{#each Array(8) as _, i (i)}
			<div class="flex flex-col gap-3 rounded-lg border p-3.5">
				<div class="flex items-center gap-2.5">
					<Skeleton class="size-8 rounded-md" />
					<Skeleton class="h-4 flex-1" />
				</div>
				<Skeleton class="h-7 w-16" />
				<Skeleton class="h-1 w-full" />
			</div>
		{/each}
	</div>
{:else if groups.length === 0}
	<EmptyState
		icon={Layers}
		title="Nothing to group"
		description="No {noun} in this view has a {label.toLowerCase()}."
		class="rounded-none border-0 bg-transparent py-16"
	/>
{:else}
	<div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b px-4 py-3">
		<div class="min-w-0">
			<div class="text-sm font-medium">{label}</div>
			{#if spec?.description}
				<div class="text-xs text-muted-foreground">{spec.description}</div>
			{/if}
		</div>
		<div
			class="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs tabular-nums text-muted-foreground"
		>
			<span>{summary}</span>
			<span class="flex items-center gap-2">
				<span>Covers {covered.toLocaleString()} of {rows.toLocaleString()} {nounPlural}</span>
				<span
					class="h-1.5 w-20 overflow-hidden rounded-full bg-muted"
					role="meter"
					aria-valuenow={coverage}
					aria-valuemin={0}
					aria-valuemax={100}
					aria-label="{nounPlural} with a {label.toLowerCase()}"
				>
					<span class="block h-full rounded-full bg-primary" style="width: {coverage}%"></span>
				</span>
			</span>
		</div>
	</div>
	<div
		class="grid grid-cols-1 gap-3 p-4 transition-opacity sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 {loading
			? 'opacity-60'
			: ''}"
	>
		{#each groups as group, i (group.value)}
			{@const id = identify(dimension, group)}
			<button
				type="button"
				class="group flex flex-col gap-3 rounded-lg border bg-card p-3.5 text-left transition-colors hover:border-primary/40 hover:bg-accent/30 focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
				aria-label="{group.label}, {group.count} {nounPlural}, filter to this group"
				onclick={() => onPick(group.query)}
			>
				<span class="flex items-start gap-2.5">
					<span
						class="flex size-8 shrink-0 items-center justify-center rounded-md border bg-background"
					>
						{#if dimension === 'country'}
							<CountryFlag code={group.value} showCode={false} />
						{:else if id.dot}
							<span class="size-2.5 rounded-full {id.dot}"></span>
						{:else if id.logo}
							<TechIcon name={id.logo} class="size-4">
								{#snippet fallback()}
									<id.icon class="size-4 text-muted-foreground" />
								{/snippet}
							</TechIcon>
						{:else}
							<id.icon class="size-4 text-muted-foreground" />
						{/if}
					</span>
					<span class="min-w-0 flex-1">
						<span
							class="block truncate text-sm font-medium {mono ? 'font-mono' : ''}"
							title={group.label}>{group.label}</span
						>
						{#if id.note}
							<span class="block truncate text-xs text-muted-foreground">{id.note}</span>
						{/if}
					</span>
					<span
						class="shrink-0 pt-0.5 font-mono text-[11px] text-muted-foreground/60 group-hover:hidden group-focus-visible:hidden"
						>{String(i + 1).padStart(2, '0')}</span
					>
					<ArrowUpRight
						class="hidden size-4 shrink-0 text-primary group-hover:block group-focus-visible:block"
					/>
				</span>
				<span class="mt-auto flex items-baseline justify-between gap-2">
					<span class="flex items-baseline gap-1.5">
						<span class="text-2xl font-semibold tracking-tight tabular-nums"
							>{group.count.toLocaleString()}</span
						>
						<span class="text-xs text-muted-foreground"
							>{group.count === 1 ? noun : nounPlural}</span
						>
					</span>
					<span class="text-xs tabular-nums text-muted-foreground">{shareLabel(group.count)}</span>
				</span>
				<span class="block h-1 w-full overflow-hidden rounded-full bg-muted">
					<span
						class="block h-full rounded-full bg-primary/70 transition-[width] duration-500"
						style="width: {Math.max(share(group.count), 1)}%"
					></span>
				</span>
			</button>
		{/each}
	</div>
{/if}
