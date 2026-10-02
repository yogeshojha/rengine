<script lang="ts" module>
	import { viewdnsApi } from '$lib/api/viewdns';
	import type { CachedCountQuery } from '$lib/types/viewdns';

	const BATCH = 100;
	let queued: CachedCountQuery[] = [];
	let flush: Promise<Record<string, number | null>> | null = null;

	const keyOf = (q: CachedCountQuery) => `${q.source}\n${q.query}\n${q.exclude}`;

	function cachedCount(q: CachedCountQuery): Promise<number | null> {
		queued.push(q);
		flush ??= Promise.resolve().then(async () => {
			const batch = Object.values(Object.fromEntries(queued.map((x) => [keyOf(x), x])));
			queued = [];
			flush = null;
			const counts: Record<string, number | null> = {};
			for (let i = 0; i < batch.length; i += BATCH) {
				const chunk = batch.slice(i, i + BATCH);
				const rows = await viewdnsApi.cachedCounts(chunk);
				chunk.forEach((x, j) => (counts[keyOf(x)] = rows[j]?.count ?? null));
			}
			return counts;
		});
		return flush.then((counts) => counts[keyOf(q)] ?? null);
	}
</script>

<script lang="ts">
	import type { DiscoverySourceType } from '$lib/types/viewdns';
	import type { WhoisSummaryData } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { DISCOVERY_SOURCE_LABELS } from '$lib/types/viewdns';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { SvelteMap } from 'svelte/reactivity';
	import { planLookups } from './lookups';

	interface Props {
		targetValue: string;
		targetType: TargetType;
		whois: WhoisSummaryData | null;
		onClick?: () => void;
	}

	let { targetValue, targetType, whois, onClick }: Props = $props();

	const cache = new SvelteMap<
		string,
		{ total: number; breakdown: { source: DiscoverySourceType; count: number; query: string }[] }
	>();

	let total = $state(0);
	let breakdown = $state<{ source: DiscoverySourceType; count: number; query: string }[]>([]);
	let loaded = $state(false);

	$effect(() => {
		void targetValue;
		void targetType;
		void whois;
		fetchCounts();
	});

	async function fetchCounts() {
		if (targetType !== TargetType.DOMAIN && targetType !== TargetType.IP) return;

		loaded = false;
		total = 0;
		breakdown = [];

		const lookups = planLookups(targetType, targetValue, whois).filter(
			(l) => l.source !== 'reverse_ns'
		);
		if (lookups.length === 0) return;

		const key = lookups.map((l) => `${l.source}:${l.queryValue}`).join('|');
		const cached = cache.get(key);
		if (cached) {
			total = cached.total;
			breakdown = cached.breakdown;
			loaded = true;
			return;
		}

		const results = await Promise.all(
			lookups.map(async (l) => {
				try {
					const count = await cachedCount({
						source: l.source,
						query: l.queryValue,
						exclude: targetValue
					});
					return { source: l.source, query: l.queryValue, count };
				} catch {
					return { source: l.source, query: l.queryValue, count: null };
				}
			})
		);

		const b: typeof breakdown = [];
		let t = 0;

		for (const { source, query, count } of results) {
			if (count && count > 0) {
				b.push({ source, count, query });
				t += count;
			}
		}

		total = t;
		breakdown = b;
		loaded = true;

		cache.set(key, { total: t, breakdown: b });
	}

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if loaded && total > 0}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button
					{...props}
					type="button"
					class="inline-flex items-center gap-1 text-2xs text-primary hover:text-primary/80 transition-colors cursor-pointer"
					onclick={handleClick}
				>
					<span class="font-medium">{total.toLocaleString()}</span>
					<span class="hidden sm:inline">
						{total === 1 ? 'discovery' : 'discoveries'}
					</span>
				</button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content side="bottom" align="start">
			<div class="space-y-1">
				<p class="font-medium">{total.toLocaleString()} discovered domains</p>
				{#each breakdown as b (b.source)}
					<p class="text-xs text-muted-foreground">
						{DISCOVERY_SOURCE_LABELS[b.source]}: {b.count.toLocaleString()} via {b.query}
					</p>
				{/each}
			</div>
		</Tooltip.Content>
	</Tooltip.Root>
{/if}
