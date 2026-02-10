<script lang="ts">
	import { TargetType, BgpStatus, type BgpSummaryData } from '$lib/types/target';
	import { Loader, TriangleAlert, Radio, RadioTower } from 'lucide-svelte';

	interface Props {
		status: BgpStatus;
		bgp: BgpSummaryData | null;
		targetType: TargetType;
		onClick?: () => void;
	}

	let { status, bgp, targetType, onClick }: Props = $props();

	let isApplicable = $derived(
		targetType === TargetType.ASN ||
			targetType === TargetType.IP ||
			targetType === TargetType.IP_RANGE
	);

	let inlineSummary = $derived.by(() => {
		if (!bgp) return '';

		switch (targetType) {
			case TargetType.ASN: {
				if (bgp.announced === false) return 'Not announced';
				const parts: string[] = [];
				if (bgp.prefix_count != null) {
					parts.push(`${bgp.prefix_count} ${bgp.prefix_count === 1 ? 'prefix' : 'prefixes'}`);
				}
				if (bgp.peer_count != null) {
					parts.push(`${bgp.peer_count} ${bgp.peer_count === 1 ? 'peer' : 'peers'}`);
				}
				return parts.join(' · ') || 'Announced';
			}
			case TargetType.IP:
			case TargetType.IP_RANGE: {
				const parts: string[] = [];
				if (bgp.asn != null) parts.push(`AS${bgp.asn}`);
				if (bgp.holder) parts.push(truncate(bgp.holder, 20));
				return parts.join(' · ');
			}
			default:
				return '';
		}
	});

	let isNotAnnounced = $derived(targetType === TargetType.ASN && bgp?.announced === false);

	function truncate(str: string, max: number): string {
		if (str.length <= max) return str;
		return str.slice(0, max - 1) + '…';
	}

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if !isApplicable}{:else if status === BgpStatus.PENDING || status === BgpStatus.ENRICHING}
	<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Loader class="h-3 w-3 animate-spin" />
		<span class="animate-pulse">BGP…</span>
	</div>
{:else if status === BgpStatus.FAILED}
	<div class="flex items-center gap-1.5 text-xs text-red-500/70 dark:text-red-400/70">
		<TriangleAlert class="h-3 w-3" />
		<span>BGP failed</span>
	</div>
{:else if status === BgpStatus.SUCCESS && bgp && inlineSummary}
	<button
		type="button"
		class="flex items-center gap-1.5 text-xs transition-colors cursor-pointer max-w-full
			{isNotAnnounced
			? 'text-amber-600 dark:text-amber-400'
			: 'text-muted-foreground hover:text-foreground'}"
		onclick={handleClick}
	>
		{#if targetType === TargetType.ASN}
			<RadioTower class="h-3 w-3 shrink-0" />
		{:else}
			<Radio class="h-3 w-3 shrink-0" />
		{/if}
		<span class="truncate font-mono">{inlineSummary}</span>
		{#if isNotAnnounced}
			<span class="inline-block h-1.5 w-1.5 rounded-full shrink-0 bg-amber-500"></span>
		{/if}
	</button>
{/if}
