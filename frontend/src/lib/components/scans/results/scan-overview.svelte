<script lang="ts">
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import StatBar from './stat-bar.svelte';
	import type { HttpAssetRead } from '$lib/types/http-asset';
	import type { IpAddressRead } from '$lib/types/ip-address';
	import type { PortRead } from '$lib/types/port';
	import {
		statusDistribution,
		techDistribution,
		webserverDistribution,
		tlsHealth,
		type StatusClass
	} from '$lib/utilities/scan-correlation';

	interface Props {
		assets: HttpAssetRead[];
		ips: IpAddressRead[];
		ports: PortRead[];
	}

	let { assets, ips, ports }: Props = $props();

	const BAR: Record<StatusClass, string> = {
		success: 'bg-success',
		info: 'bg-info',
		warning: 'bg-warning',
		destructive: 'bg-destructive',
		muted: 'bg-muted-foreground/50'
	};

	function topCounts(values: (string | null | undefined)[], n: number): [string, number][] {
		const counts: Record<string, number> = {};
		for (const v of values) {
			if (!v) continue;
			counts[v] = (counts[v] ?? 0) + 1;
		}
		return Object.entries(counts)
			.sort((a, b) => b[1] - a[1])
			.slice(0, n);
	}

	let statuses = $derived(statusDistribution(assets));
	let techs = $derived(techDistribution(assets).slice(0, 8));
	let servers = $derived(webserverDistribution(assets).slice(0, 5));
	let tls = $derived(tlsHealth(assets));
	let orgs = $derived(
		topCounts(
			ips.map((i) => i.asn_org),
			6
		)
	);
	let services = $derived(
		topCounts(
			ports.map((p) => p.service_name),
			8
		)
	);

	let expired = $derived(assets.filter((a) => a.tls_expired));
	let selfSigned = $derived(assets.filter((a) => a.tls_self_signed));
	let serverErrors = $derived(assets.filter((a) => a.status_code != null && a.status_code >= 500));
	let hasNotable = $derived(expired.length > 0 || selfSigned.length > 0 || serverErrors.length > 0);

	let assetTotal = $derived(assets.length);
</script>

<div class="space-y-3">
	<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
		{#if statuses.length}
			<Card.Root>
				<Card.Header class="pb-2"><Card.Title class="text-sm">HTTP status</Card.Title></Card.Header>
				<Card.Content class="space-y-2.5">
					{#each statuses as b (b.label)}
						<StatBar label={b.label} count={b.count} total={assetTotal} colorClass={BAR[b.klass]} />
					{/each}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if techs.length}
			<Card.Root>
				<Card.Header class="pb-2"
					><Card.Title class="text-sm">Top technologies</Card.Title></Card.Header
				>
				<Card.Content class="space-y-2.5">
					{#each techs as t (t.name)}
						<StatBar label={t.name} count={t.count} total={assetTotal} />
					{/each}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if servers.length}
			<Card.Root>
				<Card.Header class="pb-2"><Card.Title class="text-sm">Web servers</Card.Title></Card.Header>
				<Card.Content class="space-y-2.5">
					{#each servers as s (s.name)}
						<StatBar label={s.name} count={s.count} total={assetTotal} />
					{/each}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if tls.withTls > 0}
			<Card.Root>
				<Card.Header class="pb-2"><Card.Title class="text-sm">TLS health</Card.Title></Card.Header>
				<Card.Content>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<div class="text-lg font-semibold tabular-nums">{tls.withTls}</div>
							<div class="text-xs text-muted-foreground">With TLS</div>
						</div>
						<div>
							<div
								class="text-lg font-semibold tabular-nums {tls.expired ? 'text-destructive' : ''}"
							>
								{tls.expired}
							</div>
							<div class="text-xs text-muted-foreground">Expired</div>
						</div>
						<div>
							<div
								class="text-lg font-semibold tabular-nums {tls.selfSigned ? 'text-warning' : ''}"
							>
								{tls.selfSigned}
							</div>
							<div class="text-xs text-muted-foreground">Self-signed</div>
						</div>
						<div>
							<div
								class="text-lg font-semibold tabular-nums {tls.expiringSoon ? 'text-warning' : ''}"
							>
								{tls.expiringSoon}
							</div>
							<div class="text-xs text-muted-foreground">Expiring &lt;30d</div>
						</div>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}

		{#if orgs.length}
			<Card.Root>
				<Card.Header class="pb-2"><Card.Title class="text-sm">Top networks</Card.Title></Card.Header
				>
				<Card.Content class="space-y-2.5">
					{#each orgs as [name, count] (name)}
						<StatBar label={name} {count} total={ips.length} />
					{/each}
				</Card.Content>
			</Card.Root>
		{/if}

		{#if services.length}
			<Card.Root>
				<Card.Header class="pb-2"><Card.Title class="text-sm">Services</Card.Title></Card.Header>
				<Card.Content class="space-y-2.5">
					{#each services as [name, count] (name)}
						<StatBar label={name} {count} total={ports.length} />
					{/each}
				</Card.Content>
			</Card.Root>
		{/if}
	</div>

	{#if hasNotable}
		<Card.Root class="border-warning/30">
			<Card.Header class="pb-2">
				<Card.Title class="flex items-center gap-1.5 text-sm">
					<ShieldAlert class="h-4 w-4 text-warning" />
					Notable
				</Card.Title>
			</Card.Header>
			<Card.Content class="space-y-2 text-xs">
				{#if expired.length}
					<div class="flex flex-wrap items-center gap-1.5">
						<Badge variant="destructive" class="font-normal">Expired TLS</Badge>
						{#each expired.slice(0, 12) as a (a.id)}
							<span class="font-mono text-muted-foreground">{a.host}</span>
						{/each}
						{#if expired.length > 12}<span class="text-muted-foreground"
								>+{expired.length - 12}</span
							>{/if}
					</div>
				{/if}
				{#if selfSigned.length}
					<div class="flex flex-wrap items-center gap-1.5">
						<Badge variant="warning" class="font-normal">Self-signed TLS</Badge>
						{#each selfSigned.slice(0, 12) as a (a.id)}
							<span class="font-mono text-muted-foreground">{a.host}</span>
						{/each}
						{#if selfSigned.length > 12}<span class="text-muted-foreground"
								>+{selfSigned.length - 12}</span
							>{/if}
					</div>
				{/if}
				{#if serverErrors.length}
					<div class="flex flex-wrap items-center gap-1.5">
						<Badge variant="destructive" class="font-normal">5xx</Badge>
						{#each serverErrors.slice(0, 12) as a (a.id)}
							<span class="font-mono text-muted-foreground">{a.host}</span>
						{/each}
						{#if serverErrors.length > 12}<span class="text-muted-foreground"
								>+{serverErrors.length - 12}</span
							>{/if}
					</div>
				{/if}
			</Card.Content>
		</Card.Root>
	{:else if assetTotal > 0}
		<div
			class="flex items-center gap-2 rounded-lg border border-success/30 bg-success/5 p-3 text-xs text-muted-foreground"
		>
			<CircleCheck class="h-4 w-4 text-success" />
			No expired certificates, self-signed certificates, or server errors detected.
		</div>
	{/if}
</div>
