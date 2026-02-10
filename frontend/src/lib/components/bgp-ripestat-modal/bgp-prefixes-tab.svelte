<script lang="ts">
	import type { AnnouncedPrefixRead } from '$lib/types/ripestat';
	import { formatShortDate } from '$lib/utilities/dates';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import { Loader, SearchX, Network, CirclePlus } from 'lucide-svelte';

	interface Props {
		prefixes: AnnouncedPrefixRead[];
		isLoading: boolean;
		error: string | null;
		onAddAsTarget?: (value: string) => void;
	}

	let { prefixes, isLoading, error, onAddAsTarget }: Props = $props();

	const MAX_DISPLAY = 50;

	let ipv4Count = $derived(prefixes.filter((p) => p.ip_version === 4).length);
	let ipv6Count = $derived(prefixes.filter((p) => p.ip_version === 6).length);
	let displayPrefixes = $derived(prefixes.slice(0, MAX_DISPLAY));
	let hasMore = $derived(prefixes.length > MAX_DISPLAY);

	function isActive(lastSeen: string | null): boolean {
		if (!lastSeen) return true;
		const d = new Date(lastSeen);
		const now = new Date();
		const diffDays = (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24);
		return diffDays < 30;
	}

	function handleAddAsTarget(value: string) {
		onAddAsTarget?.(value);
	}
</script>

{#if isLoading}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Loader class="animate-spin" />
			</Empty.Media>
			<Empty.Title>Loading announced prefixes…</Empty.Title>
		</Empty.Header>
	</Empty.Root>
{:else if error}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<SearchX />
			</Empty.Media>
			<Empty.Title>Failed to load prefixes</Empty.Title>
			<Empty.Description>{error}</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if prefixes.length === 0}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Network />
			</Empty.Media>
			<Empty.Title>No announced prefixes</Empty.Title>
			<Empty.Description>This ASN has no visible BGP prefix announcements.</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4 py-1">
		<!-- Stats bar -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<Network class="h-4 w-4" />
				<span>
					<span class="font-medium text-foreground">{prefixes.length.toLocaleString()}</span>
					announced {prefixes.length === 1 ? 'prefix' : 'prefixes'}
				</span>
			</div>
			<div class="flex items-center gap-2">
				{#if ipv4Count > 0}
					<Badge
						variant="outline"
						class="text-[10px] font-normal gap-1 bg-blue-500/5 text-blue-600 dark:text-blue-400 border-blue-500/20"
					>
						IPv4
						<span class="font-medium">{ipv4Count.toLocaleString()}</span>
					</Badge>
				{/if}
				{#if ipv6Count > 0}
					<Badge
						variant="outline"
						class="text-[10px] font-normal gap-1 bg-purple-500/5 text-purple-600 dark:text-purple-400 border-purple-500/20"
					>
						IPv6
						<span class="font-medium">{ipv6Count.toLocaleString()}</span>
					</Badge>
				{/if}
			</div>
		</div>

		<!-- Prefix list -->
		<div class="space-y-1">
			{#each displayPrefixes as prefix}
				{@const active = isActive(prefix.last_seen)}
				<div
					class="flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-border/50 hover:border-border/80 transition-colors group/row"
				>
					<div class="flex items-center gap-3 min-w-0 flex-1">
						<span class="font-mono text-sm font-medium truncate">{prefix.prefix}</span>
						<Badge
							variant="outline"
							class="text-[10px] font-normal shrink-0 {prefix.ip_version === 4
								? 'bg-blue-500/5 text-blue-600 dark:text-blue-400 border-blue-500/20'
								: 'bg-purple-500/5 text-purple-600 dark:text-purple-400 border-purple-500/20'}"
						>
							v{prefix.ip_version}
						</Badge>
						{#if active}
							<span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0"></span>
						{/if}
					</div>

					<div class="flex items-center gap-3 shrink-0">
						{#if prefix.first_seen}
							<span class="text-[11px] text-muted-foreground hidden sm:inline">
								{formatShortDate(prefix.first_seen)}
							</span>
						{/if}

						<Tooltip.Root>
							<Tooltip.Trigger>
								<button
									class="h-6 w-6 flex items-center justify-center rounded-md opacity-0 group-hover/row:opacity-100 hover:bg-accent transition-all cursor-pointer"
									onclick={() => handleAddAsTarget(prefix.prefix)}
								>
									<CirclePlus class="h-3.5 w-3.5 text-muted-foreground" />
								</button>
							</Tooltip.Trigger>
							<Tooltip.Content>
								<p>Add {prefix.prefix} as target</p>
							</Tooltip.Content>
						</Tooltip.Root>
					</div>
				</div>
			{/each}
		</div>

		{#if hasMore}
			<p class="text-xs text-muted-foreground text-center pt-1">
				Showing {MAX_DISPLAY} of {prefixes.length.toLocaleString()} prefixes
			</p>
		{/if}
	</div>
{/if}
