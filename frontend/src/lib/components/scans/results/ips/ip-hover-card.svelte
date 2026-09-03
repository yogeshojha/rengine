<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Badge } from '$lib/components/ui/badge';
	import TechIcon from '../tech-icon.svelte';
	import { isSensitivePort } from '$lib/utilities/scan-correlation';
	import type { IpGroupRead } from '$lib/utilities/scan-insights';

	interface Props {
		group: IpGroupRead;
		children: Snippet;
	}

	let { group, children }: Props = $props();

	const MAX_PORTS = 8;
	const MAX_HOSTS = 5;

	let network = $derived(
		[group.asn ? `AS${group.asn}` : null, group.asn_org, group.country].filter(Boolean).join(' · ')
	);
</script>

<HoverCard.Root openDelay={320} closeDelay={80}>
	<HoverCard.Trigger>
		{#snippet child({ props })}
			<span {...props}>{@render children()}</span>
		{/snippet}
	</HoverCard.Trigger>
	<HoverCard.Content side="right" align="start" class="flex w-80 flex-col gap-2.5 p-3 text-xs">
		<div class="flex items-center gap-2">
			<span class="size-2 rounded-full {group.is_alive ? 'bg-success' : 'bg-muted-foreground/40'}"
			></span>
			<span class="font-mono font-medium">{group.ip}</span>
			<span class="text-muted-foreground">{group.is_alive ? 'responding' : 'no response'}</span>
			{#if group.is_cdn}
				<Badge variant="info" class="ml-auto px-1 text-[9px] font-normal">
					<TechIcon name={group.cdn_name ?? ''} class="size-2.5" />
					{group.cdn_name ?? 'CDN'}
				</Badge>
			{/if}
		</div>
		{#if network}
			<p class="text-muted-foreground">{network}{group.prefix ? ` · ${group.prefix}` : ''}</p>
		{/if}
		{#if group.ports.length}
			<div class="flex flex-wrap gap-1">
				{#each group.ports.slice(0, MAX_PORTS) as p (p.id)}
					<Badge
						variant="outline"
						class="px-1 font-mono text-[10px] font-normal {isSensitivePort(p.number)
							? 'text-warning'
							: ''}"
					>
						{p.number}{p.service_name ? `/${p.service_name}` : ''}
					</Badge>
				{/each}
				{#if group.ports.length > MAX_PORTS}
					<Badge variant="outline" class="px-1 text-[10px] font-normal text-muted-foreground">
						+{group.ports.length - MAX_PORTS}
					</Badge>
				{/if}
			</div>
		{/if}
		{#if group.hosts.length}
			<div class="flex flex-col gap-0.5">
				<span class="text-[10px] tracking-wide text-muted-foreground uppercase">
					{group.host_count}
					{group.host_count === 1 ? 'host' : 'hosts'}
				</span>
				{#each group.hosts.slice(0, MAX_HOSTS) as h (h)}
					<span class="truncate font-mono">{h}</span>
				{/each}
				{#if group.host_count > MAX_HOSTS}
					<span class="text-muted-foreground">+{group.host_count - MAX_HOSTS} more</span>
				{/if}
			</div>
		{:else}
			<p class="text-muted-foreground">No host names resolve here.</p>
		{/if}
	</HoverCard.Content>
</HoverCard.Root>
