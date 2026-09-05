<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SectionHead from '../section-head.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { CORRELATION_REASON_LABELS, type CorrelationReason } from '$lib/types/whois';
	import type { WhoisCorrelationResult } from '$lib/types/whois';
	import type { RelatedDomain } from '$lib/types/asset-query';

	interface Props {
		groups: WhoisCorrelationResult[];
		related: RelatedDomain[];
		loading: boolean;
	}

	let { groups, related, loading }: Props = $props();

	const MAX_CHIPS = 12;
	const RANK: Record<string, number> = {
		registrant: 0,
		registrant_name: 0,
		nameserver: 1,
		network: 2,
		network_cidr: 2,
		registrar: 3,
		registrar_name: 3
	};

	let ranked = $derived(
		[...groups]
			.filter((g) => g.count > 0)
			.sort((a, b) => (RANK[a.correlation_type] ?? 9) - (RANK[b.correlation_type] ?? 9))
	);
	let linked = $derived(
		new Set(ranked.flatMap((g) => g.records.map((r) => r.target_id ?? r.query_value))).size
	);
	let total = $derived(linked + related.length);
	let hasData = $derived(ranked.length > 0 || related.length > 0);

	let expanded = new SvelteSet<string>();
	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);

	function groupLabel(type: string): string {
		const spec = CORRELATION_REASON_LABELS[type as CorrelationReason];
		return spec ? `Same ${spec.match}` : type;
	}

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
</script>

{#if loading && !hasData}
	<section class="flex flex-col gap-3 border-t py-5">
		<SectionHead title="Related targets" />
		<Skeleton class="h-10 w-2/3" />
	</section>
{:else if hasData}
	<section class="flex flex-col gap-3 border-t py-5">
		<SectionHead title="Related targets" count={total} />
		<div class="flex flex-col gap-3">
			{#each ranked as g (g.correlation_type)}
				{@const open = expanded.has(g.correlation_type)}
				{@const shown = open ? g.records : g.records.slice(0, MAX_CHIPS)}
				{@const more = g.records.length - shown.length}
				<div class="grid grid-cols-1 gap-x-3 gap-y-1.5 sm:grid-cols-[11rem_minmax(0,1fr)]">
					<span class="text-xs text-muted-foreground">
						<span class="block text-[13px] font-medium text-foreground"
							>{groupLabel(g.correlation_type)}</span
						>
						<span class="wrap-anywhere">{g.correlation_value}</span>
					</span>
					<span class="flex flex-wrap items-start gap-1.5">
						{#each shown as r (r.id)}
							{#if r.target_id}
								<a
									href={ROUTES.target(r.target_id)}
									class="inline-flex h-6 max-w-full items-center rounded-md border px-2 font-mono text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
								>
									<span class="truncate">{r.query_value}</span>
								</a>
							{:else}
								<span
									class="inline-flex h-6 max-w-full items-center rounded-md border border-dashed px-2 font-mono text-xs text-muted-foreground"
								>
									<span class="truncate">{r.query_value}</span>
								</span>
							{/if}
						{/each}
						{#if more > 0}
							<button
								type="button"
								class="inline-flex h-6 items-center rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:text-foreground"
								onclick={() => expanded.add(g.correlation_type)}
							>
								+{more} more
							</button>
						{/if}
					</span>
				</div>
			{/each}
			{#each related as d (d.domain)}
				<div class="grid grid-cols-1 gap-x-3 gap-y-1.5 sm:grid-cols-[11rem_minmax(0,1fr)]">
					<span class="text-xs text-muted-foreground">
						<span class="block text-[13px] font-medium text-foreground">{d.reason_label}</span>
						<span class="wrap-anywhere"
							>{d.hostname_count}
							{d.hostname_count === 1 ? 'hostname' : 'hostnames'}{d.evidence[0]
								? ` · seen on ${d.evidence[0].seen_on}`
								: ''}</span
						>
					</span>
					<span class="flex flex-wrap items-center gap-1.5">
						<span
							class="inline-flex h-6 max-w-full items-center rounded-md border px-2 font-mono text-xs"
						>
							<span class="truncate">{d.domain}</span>
						</span>
						{#if d.is_target || added.has(d.domain)}
							<span
								class="inline-flex h-6 items-center gap-1 rounded-md bg-success/10 px-2 text-[11px] font-medium text-success"
							>
								<Check class="size-3" /> Target
							</span>
						{:else}
							<LoadingButton
								size="sm"
								variant="outline"
								class="h-6 gap-1 px-2 text-[11px]"
								loading={pending === d.domain}
								onclick={() => addTarget(d)}
							>
								<Plus class="size-3" /> Add target
							</LoadingButton>
						{/if}
					</span>
				</div>
			{/each}
		</div>
	</section>
{/if}
