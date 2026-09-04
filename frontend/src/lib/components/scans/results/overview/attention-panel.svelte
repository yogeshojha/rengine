<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import ShieldOff from '@lucide/svelte/icons/shield-off';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Plug from '@lucide/svelte/icons/plug';
	import Server from '@lucide/svelte/icons/server';
	import Link2Off from '@lucide/svelte/icons/link-2-off';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import Check from '@lucide/svelte/icons/check';
	import Plus from '@lucide/svelte/icons/plus';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from './panel-head.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { filterToken } from '$lib/utilities/scan-insights';
	import type { IconComponent } from '$lib/config/icons';
	import type { ScanRead } from '$lib/types/scan';
	import type { RelatedDomain } from '$lib/types/asset-query';
	import type { InsightAttention, InsightCluster } from '$lib/utilities/scan-insights';

	interface Props {
		scan: ScanRead;
		attention: InsightAttention[];
		clusters: InsightCluster[];
		related: RelatedDomain[];
		assessed: boolean;
		live: boolean;
		loading: boolean;
		errored: boolean;
		onFilter: (search: string) => void;
		onRescan: () => void;
		onRetry: () => void;
	}

	let {
		scan,
		attention,
		clusters,
		related,
		assessed,
		live,
		loading,
		errored,
		onFilter,
		onRescan,
		onRetry
	}: Props = $props();

	type Tone = InsightAttention['tone'];
	interface Finding {
		key: string;
		tone: Tone;
		icon: IconComponent;
		text: string;
		count: number;
		filter: string;
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
	const CHECKED =
		'Certificates, dangling CNAME records, CDN and WAF coverage, server errors, login panels and exposed services were checked.';

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

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead
		title="Needs attention"
		description="Exposure findings and related domains from this scan"
	>
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
		{:else if errored && !hasTiles}
			<EmptyState compact icon={TriangleAlert} title="Findings could not be loaded">
				<Button variant="outline" size="sm" onclick={onRetry}>Retry</Button>
			</EmptyState>
		{:else if live && !assessed && !hasTiles}
			<EmptyState
				compact
				icon={ShieldCheck}
				title="Exposure checks start once HTTP probing completes"
				description="Findings appear here as the scan progresses."
			/>
		{:else if !assessed && !hasTiles}
			<EmptyState
				compact
				icon={ShieldOff}
				title="Exposure checks not performed"
				description={scan.status === 'completed'
					? 'This engine does not probe HTTP services.'
					: 'The scan stopped before HTTP probing.'}
			>
				<Button variant="outline" size="sm" onclick={onRescan}>Re-scan</Button>
			</EmptyState>
		{:else if !hasTiles}
			<EmptyState compact icon={ShieldCheck} title="No findings" description={CHECKED} />
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
						onclick={() => onFilter(f.filter)}
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
			{#if !assessed}
				<div class="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
					<span>
						{live
							? 'Exposure checks start once HTTP probing completes.'
							: scan.status === 'completed'
								? 'Exposure checks not performed. This engine does not probe HTTP services.'
								: 'Exposure checks not performed. The scan stopped before HTTP probing.'}
					</span>
					{#if !live}
						<Button variant="outline" size="sm" onclick={onRescan}>Re-scan</Button>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</Card.Root>
