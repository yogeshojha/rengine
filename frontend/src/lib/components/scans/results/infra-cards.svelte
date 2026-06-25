<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Plug from '@lucide/svelte/icons/plug';
	import Globe from '@lucide/svelte/icons/globe';
	import { Badge } from '$lib/components/ui/badge';
	import { Input } from '$lib/components/ui/input';
	import type { IpGroup } from '$lib/utilities/scan-correlation';

	interface Props {
		groups: IpGroup[];
	}

	let { groups }: Props = $props();

	let search = $state('');

	let filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		if (!q) return groups;
		return groups.filter(
			(g) =>
				g.ip.includes(q) ||
				(g.meta?.asn_org ?? '').toLowerCase().includes(q) ||
				g.hosts.some((h) => h.toLowerCase().includes(q)) ||
				g.meta?.ptr_hostnames?.some((h) => h.toLowerCase().includes(q))
		);
	});

	const MAX_HOSTS = 8;
</script>

<div class="space-y-3">
	<div class="relative max-w-sm">
		<Search class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
		<Input bind:value={search} placeholder="Filter IP, org, host…" class="h-8 pl-8 text-sm" />
	</div>

	<div class="grid gap-3 lg:grid-cols-2">
		{#each filtered as g (g.ip)}
			<div class="space-y-3 rounded-lg border border-border p-3">
				<div class="flex items-start justify-between gap-2">
					<div class="space-y-0.5">
						<div class="flex items-center gap-2">
							{#if g.meta?.is_alive === true}
								<span class="h-2 w-2 rounded-full bg-success" title="alive"></span>
							{:else if g.meta?.is_alive === false}
								<span class="h-2 w-2 rounded-full bg-muted-foreground/40" title="not responding"
								></span>
							{/if}
							<span class="font-mono text-sm">{g.ip}</span>
							<Badge
								variant="outline"
								class="px-1 py-0 text-[10px] font-normal text-muted-foreground"
							>
								v{g.meta?.version ?? 4}
							</Badge>
						</div>
						{#if g.meta?.asn}
							<div class="text-xs text-muted-foreground">
								AS{g.meta.asn}{g.meta.asn_org ? ` · ${g.meta.asn_org}` : ''}{g.meta.country
									? ` · ${g.meta.country}`
									: ''}
							</div>
						{/if}
					</div>
					{#if g.meta?.is_cdn}
						<Badge variant="info" class="font-normal">{g.meta.cdn_name ?? 'CDN'}</Badge>
					{/if}
				</div>

				{#if g.meta?.ptr_hostnames?.length}
					<div class="font-mono text-[11px] text-muted-foreground">
						{g.meta.ptr_hostnames.join(', ')}
					</div>
				{/if}

				{#if g.ports.length}
					<div class="space-y-1">
						<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
							<Plug class="h-3 w-3" />
							{g.ports.length} open {g.ports.length === 1 ? 'port' : 'ports'}
						</div>
						<div class="flex flex-wrap gap-1">
							{#each g.ports as p (p.id)}
								<Badge variant="outline" class="font-mono text-[11px] font-normal">
									{p.number}{p.service_name ? `/${p.service_name}` : ''}
								</Badge>
							{/each}
						</div>
					</div>
				{/if}

				{#if g.hosts.length}
					<div class="space-y-1">
						<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
							<Globe class="h-3 w-3" />
							{g.hosts.length}
							{g.hosts.length === 1 ? 'host' : 'hosts'} resolve here
						</div>
						<div class="flex flex-wrap gap-1">
							{#each g.hosts.slice(0, MAX_HOSTS) as h (h)}
								<Badge variant="secondary" class="font-mono text-[11px] font-normal">{h}</Badge>
							{/each}
							{#if g.hosts.length > MAX_HOSTS}
								<Badge variant="secondary" class="text-[11px] font-normal text-muted-foreground">
									+{g.hosts.length - MAX_HOSTS}
								</Badge>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
