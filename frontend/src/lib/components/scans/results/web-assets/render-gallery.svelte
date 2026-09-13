<script lang="ts">
	import ImageOff from '@lucide/svelte/icons/image-off';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Filter from '@lucide/svelte/icons/filter';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { screenshotUrl } from '$lib/utilities/media';
	import type { RenderGroups } from '$lib/types/subdomain';
	import { SvelteSet } from 'svelte/reactivity';
	import Camera from '@lucide/svelte/icons/camera';

	interface Props {
		data: RenderGroups | null;
		loading: boolean;
		failed?: boolean;
		onRetry?: () => void;
		onFilter: (token: string) => void;
		onHost: (name: string) => void;
	}

	let { data, loading, failed = false, onRetry, onFilter, onHost }: Props = $props();

	const MAX_HOSTS = 6;
	const broken = new SvelteSet<string>();
	const expanded = new SvelteSet<string>();

	function toggle(hash: string) {
		if (expanded.has(hash)) expanded.delete(hash);
		else expanded.add(hash);
	}
</script>

{#if loading && !data}
	<div class="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
		{#each Array(10) as _, i (i)}
			<Skeleton class="aspect-video w-full rounded-lg" />
		{/each}
	</div>
{:else if failed}
	<EmptyState
		icon={TriangleAlert}
		title="Renders not loaded"
		class="rounded-none border-0 bg-transparent py-16"
	>
		{#if onRetry}
			<Button variant="outline" size="sm" onclick={() => onRetry()}>Retry</Button>
		{/if}
	</EmptyState>
{:else if data && data.groups.length === 0}
	<EmptyState
		icon={Camera}
		title="No screenshots to group"
		class="rounded-none border-0 bg-transparent py-16"
	/>
{:else if data}
	<div class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border px-4 py-2.5">
		<span class="text-xs text-muted-foreground">
			<span class="font-medium text-foreground tabular-nums">{data.total_groups}</span> renders
		</span>
		<span class="text-xs text-muted-foreground">
			<span class="font-medium text-foreground tabular-nums">{data.grouped}</span> shared
		</span>
		<span class="text-xs text-muted-foreground">
			<span class="font-medium text-foreground tabular-nums">{data.ungrouped}</span> unique
		</span>
		{#if data.blank}
			<span class="text-xs text-muted-foreground">
				<span class="font-medium text-foreground tabular-nums">{data.blank}</span> blank
			</span>
		{/if}
		{#if data.unrendered}
			<span class="text-xs text-muted-foreground">
				<span class="font-medium text-foreground tabular-nums">{data.unrendered}</span> not captured
			</span>
		{/if}
	</div>

	<div
		class="grid grid-cols-2 gap-3 p-4 transition-opacity sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 {loading
			? 'opacity-60'
			: ''}"
	>
		{#each data.groups as g (g.hash)}
			{@const url = broken.has(g.hash) ? null : screenshotUrl(g.screenshot_path)}
			{@const open = expanded.has(g.hash)}
			<div class="flex flex-col overflow-hidden rounded-lg border border-border bg-card text-left">
				<div class="relative">
					{#if g.count > 1}
						<div
							class="absolute -top-0.5 right-2 left-2 h-1 rounded-t-sm border border-b-0 border-border bg-muted/60"
						></div>
					{/if}
					<button
						type="button"
						onclick={() => onFilter(g.query)}
						aria-label="Filter to the {g.count} web assets that render this page"
						class="group relative block aspect-video w-full overflow-hidden border-b border-border bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					>
						{#if url}
							<img
								src={url}
								alt="Rendered page shared by {g.count} web assets"
								loading="lazy"
								onerror={() => broken.add(g.hash)}
								class="h-full w-full object-cover object-top transition-transform duration-300 group-hover:scale-[1.02]"
							/>
						{:else}
							<div
								class="flex h-full w-full flex-col items-center justify-center gap-1 text-muted-foreground"
							>
								<ImageOff class="size-5" />
								<span class="text-2xs">No screenshot</span>
							</div>
						{/if}
						<Badge
							variant={g.count > 1 ? 'default' : 'outline'}
							class="absolute top-1.5 left-1.5 px-1.5 font-mono text-2xs tabular-nums backdrop-blur {g.count >
							1
								? ''
								: 'border-border/60 bg-background/90'}"
						>
							{g.count}
						</Badge>
						<span
							class="absolute right-1.5 bottom-1.5 flex size-6 items-center justify-center rounded-md border border-border/60 bg-background/90 text-muted-foreground opacity-0 backdrop-blur transition-opacity group-hover:opacity-100"
						>
							<Filter class="size-3" />
						</span>
					</button>
				</div>

				<div class="flex min-w-0 flex-col gap-1 p-2.5">
					{#if g.label}
						<span class="truncate text-xs font-medium">{g.label}</span>
					{:else}
						<span class="truncate text-xs text-muted-foreground italic">No page title</span>
					{/if}
					<div class="flex flex-col gap-0.5">
						{#each open ? g.hosts : g.hosts.slice(0, MAX_HOSTS) as host (host)}
							<button
								type="button"
								onclick={() => onHost(host)}
								class="truncate text-left font-mono text-2xs text-muted-foreground hover:text-foreground hover:underline"
							>
								{host}
							</button>
						{/each}
					</div>
					{#if g.hosts.length > MAX_HOSTS}
						<Button
							variant="ghost"
							size="sm"
							class="h-6 justify-start gap-1 px-1 text-2xs text-muted-foreground"
							onclick={() => toggle(g.hash)}
						>
							<ChevronDown class="size-3 transition-transform {open ? 'rotate-180' : ''}" />
							{open ? 'Show fewer' : `${g.hosts.length - MAX_HOSTS} more`}
						</Button>
					{/if}
					{#if g.count > g.hosts.length}
						<button
							type="button"
							onclick={() => onFilter(g.query)}
							class="truncate text-left text-2xs text-muted-foreground hover:text-foreground hover:underline"
						>
							Open all {g.count}
						</button>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}
