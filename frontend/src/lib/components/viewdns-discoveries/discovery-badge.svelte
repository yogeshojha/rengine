<script lang="ts">
	import { viewdnsApi } from '$lib/api/viewdns';
	import type { ViewDNSCacheRead, DiscoverySourceType } from '$lib/types/viewdns';
	import type { WhoisSummaryData } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { DISCOVERY_SOURCE_LABELS } from '$lib/types/viewdns';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Sparkles } from 'lucide-svelte';
	import { SvelteMap } from 'svelte/reactivity';

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

		const cached = cache.get(targetValue);
		if (cached) {
			total = cached.total;
			breakdown = cached.breakdown;
			loaded = true;
			return;
		}

		const lookups = planLookups();
		if (lookups.length === 0) return;

		try {
			const results = await Promise.all(
				lookups.map(async (l) => {
					try {
						const result = await l.fetch(l.queryValue, true);
						return { source: l.source, query: l.queryValue, result };
					} catch {
						return { source: l.source, query: l.queryValue, result: null };
					}
				})
			);

			const b: typeof breakdown = [];
			let t = 0;

			for (const { source, query, result } of results) {
				if (result && result.result_count > 0) {
					const count = Math.max(0, result.result_count - 1);
					if (count > 0) {
						b.push({ source, count, query });
						t += count;
					}
				}
			}

			total = t;
			breakdown = b;
			loaded = true;

			cache.set(targetValue, { total: t, breakdown: b });
		} catch {
			// nothing
		}
	}

	function planLookups(): {
		source: DiscoverySourceType;
		queryValue: string;
		fetch: (q: string, cachedOnly: boolean) => Promise<ViewDNSCacheRead | null>;
	}[] {
		const lookups: ReturnType<typeof planLookups> = [];

		if (targetType === TargetType.DOMAIN && whois) {
			if (whois.registrant_name) {
				lookups.push({
					source: 'reverse_whois',
					queryValue: whois.registrant_name,
					fetch: viewdnsApi.reverseWhois
				});
			}
		} else if (targetType === TargetType.IP) {
			lookups.push({
				source: 'reverse_ip',
				queryValue: targetValue,
				fetch: viewdnsApi.reverseIp
			});
		}

		return lookups;
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
					class="inline-flex items-center gap-1 text-[11px] text-chart-1 hover:text-chart-1/80 transition-colors cursor-pointer"
					onclick={handleClick}
				>
					<Sparkles class="h-3 w-3" />
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
