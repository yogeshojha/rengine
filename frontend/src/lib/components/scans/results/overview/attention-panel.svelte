<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import ShieldOff from '@lucide/svelte/icons/shield-off';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Plug from '@lucide/svelte/icons/plug';
	import Server from '@lucide/svelte/icons/server';
	import Link2Off from '@lucide/svelte/icons/link-2-off';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import CloudOff from '@lucide/svelte/icons/cloud-off';
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import Check from '@lucide/svelte/icons/check';
	import Plus from '@lucide/svelte/icons/plus';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import OriginDialog from '../origin-dialog.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { filterToken } from '$lib/utilities/scan-insights';
	import type { IconComponent } from '$lib/config/icons';
	import type { RelatedDomain } from '$lib/types/asset-query';
	import { ORIGIN_EXPOSED, type OriginExposure, type OriginFinding } from '$lib/utilities/origins';
	import type { InsightAttention, InsightCluster } from '$lib/utilities/scan-insights';

	interface Props {
		attention: InsightAttention[];
		clusters: InsightCluster[];
		related: RelatedDomain[];
		origins: OriginExposure | null;
		loading: boolean;
		errored: boolean;
		onFilter: (search: string) => void;
		onTab: (tab: string, filter?: string) => void;
	}

	let { attention, clusters, related, origins, loading, errored, onFilter, onTab }: Props =
		$props();

	type Tone = InsightAttention['tone'];
	interface Finding {
		key: string;
		tone: Tone;
		icon: IconComponent;
		text: string;
		count: number;
		filter: string;
		open?: () => void;
	}

	const ICON: Record<string, IconComponent> = {
		takeover: Link2Off,
		expired: Lock,
		expiring: Lock,
		selfsigned: Lock,
		nowaf: ShieldOff,
		server: CircleX,
		auth: KeyRound,
		sensitive: Plug
	};
	const TONE: Record<Tone, { label: string; rank: number; dot: string }> = {
		destructive: { label: 'High', rank: 0, dot: 'bg-destructive' },
		warning: { label: 'Medium', rank: 1, dot: 'bg-warning' }
	};

	let originFindings = $derived(origins?.findings ?? []);
	let bypasses = $derived(originFindings.filter((f) => f.kind === ORIGIN_EXPOSED));
	let mismatches = $derived(originFindings.filter((f) => f.kind !== ORIGIN_EXPOSED));
	let originList = $state<OriginFinding[]>([]);
	let originIndex = $state(0);
	let originOpen = $state(false);
	function showOrigins(list: OriginFinding[]) {
		originList = list;
		originIndex = 0;
		originOpen = true;
	}

	let findings = $derived.by<Finding[]>(() => {
		const out: Finding[] = attention.map((a) => ({
			key: a.key,
			tone: a.tone,
			icon: ICON[a.key] ?? TriangleAlert,
			text: a.label,
			count: a.count,
			filter: a.filter
		}));
		for (const c of clusters) {
			if (c.kind === 'ip' && isPrivateIp(c.value))
				out.push({
					key: `private:${c.value}`,
					tone: 'warning',
					icon: Server,
					text: `Hosts resolving to private address ${c.value}`,
					count: c.count,
					filter: filterToken('ip', c.value)
				});
		}
		if (bypasses.length)
			out.push({
				key: 'origin',
				tone: 'destructive',
				icon: CloudOff,
				text:
					bypasses.length === 1
						? 'Origin reachable outside the CDN'
						: 'Origins reachable outside the CDN',
				count: bypasses.length,
				filter: '',
				open: () => showOrigins(bypasses)
			});
		if (mismatches.length)
			out.push({
				key: 'origin-mismatch',
				tone: 'warning',
				icon: ArrowLeftRight,
				text:
					mismatches.length === 1
						? 'Address serving a different site'
						: 'Addresses serving a different site',
				count: mismatches.length,
				filter: '',
				open: () => showOrigins(mismatches)
			});
		return out.sort((a, b) => TONE[a.tone].rank - TONE[b.tone].rank || b.count - a.count);
	});
	let high = $derived(findings.filter((f) => f.tone === 'destructive').length);
	let medium = $derived(findings.length - high);
	let hasTiles = $derived(findings.length > 0 || related.length > 0);

	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);

	async function addTarget(domain: RelatedDomain) {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return;
		pending = domain.domain;
		try {
			await targetsApi.create({ target_value: domain.domain, project_slug: slug });
			added.add(domain.domain);
			toast.success(`${domain.domain} added as a target`);
		} catch {
			toast.error(`Could not add ${domain.domain}`);
		} finally {
			pending = null;
		}
	}

	function relatedText(d: RelatedDomain): string {
		return `${d.reason_label} · ${d.hostname_count} ${d.hostname_count === 1 ? 'hostname' : 'hostnames'}`;
	}
</script>

{#if hasTiles || (loading && !errored)}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Needs attention">
			{#if related.length > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-primary" aria-hidden="true"></span>
					{related.length} related {related.length === 1 ? 'domain' : 'domains'}
				</span>
			{/if}
			{#if high > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-destructive" aria-hidden="true"></span>
					{high} high
				</span>
			{/if}
			{#if medium > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-warning" aria-hidden="true"></span>
					{medium} medium
				</span>
			{/if}
		</PanelHead>

		<div class="p-5">
			{#if loading && !hasTiles}
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each Array(4) as _, i (i)}
						<Skeleton class="h-28 w-full rounded-lg" />
					{/each}
				</div>
			{:else}
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each related as d (d.domain)}
						{@const done = d.is_target || added.has(d.domain)}
						<div
							class="flex flex-col gap-3 rounded-lg border border-primary/30 bg-primary/[0.03] p-4"
						>
							<span class="flex h-6 items-center justify-between gap-2 text-[11px]">
								<span class="flex items-center gap-1.5 text-muted-foreground">
									<Waypoints class="size-3.5 text-primary" />
									Related domain
								</span>
								{#if done}
									<Badge variant="success" class="gap-1">
										<Check class="size-3" />
										Target
									</Badge>
								{:else}
									<LoadingButton
										size="sm"
										variant="outline"
										class="h-6 gap-1 px-2 text-[11px]"
										loading={pending === d.domain}
										onclick={() => addTarget(d)}
									>
										<Plus class="size-3" />
										Add target
									</LoadingButton>
								{/if}
							</span>
							<Hint text={d.domain}>
								{#snippet child(props)}
									<span {...props} class="truncate font-mono text-xl leading-none font-semibold">
										{d.domain}
									</span>
								{/snippet}
							</Hint>
							<span class="line-clamp-2 text-sm leading-5 text-muted-foreground"
								>{relatedText(d)}</span
							>
							{#if d.evidence[0]}
								<span class="truncate text-xs leading-4 text-muted-foreground">
									Seen on <span class="font-mono">{d.evidence[0].seen_on}</span>
								</span>
							{/if}
						</div>
					{/each}
					{#each findings as f (f.key)}
						{@const Icon = f.icon}
						{@const tone = TONE[f.tone]}
						<button
							type="button"
							class="group flex cursor-pointer flex-col gap-3 rounded-lg border border-border/70 p-4 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
							onclick={() => (f.open ? f.open() : onFilter(f.filter))}
						>
							<span class="flex h-6 items-center justify-between gap-2 text-[11px]">
								<span class="flex items-center gap-1.5 text-muted-foreground">
									<span class="size-1.5 rounded-full {tone.dot}" aria-hidden="true"></span>
									{tone.label}
								</span>
								<Icon class="size-3.5 text-muted-foreground/70" />
							</span>
							<span class="text-2xl leading-none font-semibold tracking-tight">
								{f.count.toLocaleString()}
							</span>
							<span
								class="line-clamp-2 text-sm leading-5 text-muted-foreground transition-colors group-hover:text-foreground"
							>
								{f.text}
							</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</Card.Root>
{/if}

<OriginDialog
	finding={originList[originIndex] ?? null}
	index={originIndex}
	total={originList.length}
	open={originOpen}
	onOpenChange={(v) => (originOpen = v)}
	onStep={(next) => (originIndex = next)}
	onServices={(filter) => onTab('services', filter)}
/>
