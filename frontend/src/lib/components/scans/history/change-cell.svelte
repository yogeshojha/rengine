<script lang="ts">
	import * as HoverCard from '$lib/components/ui/hover-card';
	import TrendingUp from '@lucide/svelte/icons/trending-up';
	import TrendingDown from '@lucide/svelte/icons/trending-down';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { isOpenStatus } from '$lib/utilities/scan-status';
	import type { ScanRead } from '$lib/types/scan';
	import { compactCount } from '$lib/utilities/numbers';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const PREVIEW = 6;

	interface Props {
		projectId: string;
		scan: ScanRead;
		onCompare: () => void;
	}

	let { projectId, scan, onCompare }: Props = $props();

	let added = $derived(scan.new_subdomains ?? 0);
	let gone = $derived(scan.gone_subdomains ?? 0);
	let open = $derived(isOpenStatus(scan.status));
	let names = $state<string[] | null>(null);
	let failed = $state(false);

	function load() {
		if (names || !added) return;
		subdomainsApi
			.search(projectId, scan.id, {
				q: 'is:new',
				statuses: [],
				tech: [],
				services: [],
				cert: [],
				hygiene: [],
				posture: [],
				sources: [],
				cdn: 'any',
				waf: 'any',
				live: false,
				screenshot: false,
				issues: false,
				new: false,
				sort: 'name',
				order: 'asc',
				limit: PREVIEW,
				offset: 0
			})
			.then((r) => (names = r.items.map((i) => i.name)))
			.catch(() => (failed = true));
	}
</script>

{#if scan.is_first_scan}
	<span class="text-xs text-muted-foreground">First run</span>
{:else if !added && !gone}
	<span class="text-xs text-muted-foreground">{open ? 'None yet' : 'No change'}</span>
{:else}
	<HoverCard.Root openDelay={300} closeDelay={80} onOpenChange={(o) => o && load()}>
		<HoverCard.Trigger
			href={ROUTES.results(WEB.tab, scan.id, { [WEB.queryParam]: 'is:new' })}
			onclick={(e: MouseEvent) => e.stopPropagation()}
			class="inline-flex items-center gap-2 rounded font-mono text-xs tabular-nums focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			aria-label="{added} new and {gone} gone {WEB.nounPlural}"
		>
			{#if added}
				<span class="inline-flex items-center gap-0.5 font-semibold text-success">
					<TrendingUp class="size-3.5" />{compactCount(added)}
				</span>
			{/if}
			{#if gone}
				<span class="inline-flex items-center gap-0.5 font-semibold text-destructive">
					<TrendingDown class="size-3.5" />{compactCount(gone)}
				</span>
			{/if}
		</HoverCard.Trigger>
		<HoverCard.Content class="w-80 p-0" align="start">
			{#if added}
				<div class="border-b px-3 py-2 text-xs font-medium">
					{added.toLocaleString()} new {added === 1 ? WEB.noun : WEB.nounPlural}{open
						? ' so far'
						: ''}
				</div>
				{#if failed}
					<p class="px-3 py-2 text-xs text-muted-foreground">Names not loaded.</p>
				{:else if !names}
					<div class="space-y-2 px-3 py-3">
						{#each { length: Math.min(added, 3) } as _, i (i)}
							<div class="h-3 animate-pulse rounded bg-muted"></div>
						{/each}
					</div>
				{:else}
					<ul class="px-3 py-1.5">
						{#each names as n (n)}
							<li class="truncate py-0.5 font-mono text-xs">{n}</li>
						{/each}
						{#if added > names.length}
							<li class="py-0.5 text-2xs text-muted-foreground">
								{(added - names.length).toLocaleString()} more
							</li>
						{/if}
					</ul>
				{/if}
			{/if}
			{#if gone}
				<div class="border-t px-3 py-2 text-xs">
					<span class="font-medium">{gone.toLocaleString()} gone</span>
				</div>
			{/if}
			<div class="flex items-center gap-3 border-t px-3 py-2 text-2xs">
				{#if added}
					<a
						href={ROUTES.results(WEB.tab, scan.id, { [WEB.queryParam]: 'is:new' })}
						class="text-primary hover:text-primary/80"
					>
						Open new {WEB.nounPlural}
					</a>
				{/if}
				<button type="button" class="text-primary hover:text-primary/80" onclick={onCompare}>
					Compare with previous
				</button>
			</div>
		</HoverCard.Content>
	</HoverCard.Root>
{/if}
