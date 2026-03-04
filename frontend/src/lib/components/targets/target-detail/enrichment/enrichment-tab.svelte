<script lang="ts">
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { toast } from 'svelte-sonner';
	import EnrichmentWidget from './enrichment-widget.svelte';
	import DnsSection from './dns-section.svelte';
	import WhoisSection from './whois-section.svelte';
	import BgpSection from './bgp-section.svelte';
	import EnrichmentSkeleton from './enrichment-skeleton.svelte';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	let detail = $state<TargetDetailRead | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let refreshingDns = $state(false);
	let refreshingWhois = $state(false);
	let refreshingBgp = $state(false);

	let showDns = $derived(
		target.target_type === TargetType.DOMAIN || target.target_type === TargetType.URL
	);
	let showBgp = $derived(
		target.target_type === TargetType.IP ||
			target.target_type === TargetType.IP_RANGE ||
			target.target_type === TargetType.ASN
	);

	let dnsStatus = $derived(detail?.dns_status ?? target.dns_status);
	let whoisStatus = $derived(detail?.whois_status ?? target.whois_status);
	let bgpStatus = $derived(detail?.bgp_status ?? target.bgp_status);

	async function fetchDetail() {
		loading = true;
		error = null;
		try {
			detail = await targetsApi.getDetail(target.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load enrichment data';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (target.id) fetchDetail();
	});

	async function handleRefreshDns() {
		refreshingDns = true;
		try {
			await targetsApi.refreshDns(target.id);
			toast.success('DNS refresh initiated');
			setTimeout(fetchDetail, 2000);
		} catch {
			toast.error('Failed to refresh DNS');
		} finally {
			refreshingDns = false;
		}
	}

	async function handleRefreshWhois() {
		refreshingWhois = true;
		try {
			await targetsApi.refreshWhois(target.id);
			toast.success('WHOIS refresh initiated');
			setTimeout(fetchDetail, 2000);
		} catch {
			toast.error('Failed to refresh WHOIS');
		} finally {
			refreshingWhois = false;
		}
	}

	async function handleRefreshBgp() {
		refreshingBgp = true;
		try {
			await targetsApi.refreshBgp(target.id);
			toast.success('BGP refresh initiated');
			setTimeout(fetchDetail, 2000);
		} catch {
			toast.error('Failed to refresh BGP');
		} finally {
			refreshingBgp = false;
		}
	}
</script>

{#if loading}
	<EnrichmentSkeleton />
{:else if error}
	<div class="flex flex-col items-center justify-center py-16 text-center">
		<p class="text-sm text-destructive">{error}</p>
		<button
			class="mt-3 text-xs text-muted-foreground underline-offset-4 hover:underline"
			onclick={fetchDetail}
		>
			Try again
		</button>
	</div>
{:else if detail}
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
		<EnrichmentWidget
			title="WHOIS"
			status={whoisStatus}
			error={detail.whois_error}
			queriedAt={detail.whois?.queried_at}
			onRefresh={handleRefreshWhois}
			isRefreshing={refreshingWhois}
			class="lg:col-span-1 {!showDns && !showBgp ? 'lg:col-span-2' : ''}"
		>
			{#if detail.whois}
				<WhoisSection record={detail.whois} targetType={target.target_type} />
			{/if}
		</EnrichmentWidget>

		{#if showBgp && detail.bgp}
			<EnrichmentWidget
				title="BGP"
				status={bgpStatus}
				onRefresh={handleRefreshBgp}
				isRefreshing={refreshingBgp}
			>
				<BgpSection bgp={detail.bgp} targetType={target.target_type} />
			</EnrichmentWidget>
		{/if}

		{#if showDns}
			<EnrichmentWidget
				title="DNS Records"
				status={dnsStatus}
				error={detail.dns_error}
				queriedAt={detail.dns?.queried_at}
				onRefresh={handleRefreshDns}
				isRefreshing={refreshingDns}
				class="lg:col-span-2"
			>
				{#if detail.dns}
					<DnsSection lookup={detail.dns} />
				{/if}
			</EnrichmentWidget>
		{/if}
	</div>
{/if}
