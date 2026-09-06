<script lang="ts">
	import type { AnnouncedPrefixRead } from '$lib/types/ripestat';
	import { formatShortDate, MS_PER_DAY } from '$lib/utilities/dates';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Network from '@lucide/svelte/icons/network';
	import CirclePlus from '@lucide/svelte/icons/circle-plus';
	import { Spinner } from '$lib/components/ui/spinner';

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
		const diffDays = (now.getTime() - d.getTime()) / MS_PER_DAY;
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
				<Spinner />
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
			<Empty.Title>Prefixes could not be loaded</Empty.Title>
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
						class="text-[10px] font-normal gap-1 text-muted-foreground border-border/60"
					>
						IPv4
						<span class="font-medium">{ipv4Count.toLocaleString()}</span>
					</Badge>
				{/if}
				{#if ipv6Count > 0}
					<Badge
						variant="outline"
						class="text-[10px] font-normal gap-1 text-muted-foreground border-border/60"
					>
						IPv6
						<span class="font-medium">{ipv6Count.toLocaleString()}</span>
					</Badge>
				{/if}
			</div>
		</div>

		<div class="space-y-1">
			{#each displayPrefixes as prefix (prefix.prefix)}
				{@const active = isActive(prefix.last_seen)}
				<div
					class="flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-border/50 hover:border-border/80 transition-colors group/row"
				>
					<div class="flex items-center gap-3 min-w-0 flex-1">
						<span class="font-mono text-sm font-medium truncate">{prefix.prefix}</span>
						<Badge
							variant="outline"
							class="text-[10px] font-normal shrink-0 text-muted-foreground border-border/60"
						>
							v{prefix.ip_version}
						</Badge>
						{#if active}
							<span class="inline-block h-1.5 w-1.5 rounded-full bg-chart-1 shrink-0"></span>
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
								{#snippet child({ props })}
									<button
										{...props}
										class="h-9 w-9 sm:h-6 sm:w-6 flex items-center justify-center rounded-md opacity-100 sm:opacity-0 sm:group-hover/row:opacity-100 hover:bg-accent transition-all cursor-pointer"
										onclick={() => handleAddAsTarget(prefix.prefix)}
									>
										<CirclePlus class="h-3.5 w-3.5 text-muted-foreground" />
									</button>
								{/snippet}
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
