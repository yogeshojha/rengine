<script lang="ts">
	import ImageOff from '@lucide/svelte/icons/image-off';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Lock from '@lucide/svelte/icons/lock';
	import { Badge } from '$lib/components/ui/badge';
	import TechIcon from '../tech-icon.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { screenshotUrl } from '$lib/utilities/media';
	import { httpStatusClass, STATUS_DOT } from '$lib/utilities/scan-correlation';
	import { certState } from '$lib/utilities/scan-insights';
	import { RESULTS_SCROLL } from '$lib/utilities/scan-status';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		items: SubdomainRead[];
		loading: boolean;
		selectedId: string | null;
		onOpen: (s: SubdomainRead) => void;
	}

	let { items, loading, selectedId, onOpen }: Props = $props();

	const MAX_TECH = 2;
	const stop = (e: Event) => e.stopPropagation();
	const broken = new SvelteSet<string>();
</script>

<ScrollArea class={RESULTS_SCROLL}>
	<div
		class="grid grid-cols-2 gap-3 pr-3 transition-opacity sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 {loading
			? 'opacity-60'
			: ''}"
	>
		{#each items as s (s.id)}
			{@const url = broken.has(s.id) ? null : screenshotUrl(s.screenshot_path)}
			{@const cert = certState(s)}
			{@const cls = httpStatusClass(s.http_status)}
			<div
				role="button"
				tabindex={0}
				class="group relative flex cursor-pointer flex-col overflow-hidden rounded-lg border border-border bg-card text-left transition-colors hover:border-foreground/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {selectedId ===
				s.id
					? 'ring-2 ring-primary'
					: ''}"
				onclick={() => onOpen(s)}
				onkeydown={(e) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						onOpen(s);
					}
				}}
			>
				<div
					class="relative aspect-video w-full overflow-hidden border-b border-border bg-muted/40"
				>
					{#if url}
						<img
							src={url}
							alt="Screenshot of {s.name}"
							loading="lazy"
							onerror={() => broken.add(s.id)}
							class="h-full w-full object-cover object-top transition-transform duration-300 group-hover:scale-[1.02]"
						/>
					{:else}
						<div
							class="flex h-full w-full flex-col items-center justify-center gap-1 text-muted-foreground"
						>
							<ImageOff class="size-5" />
							<span class="text-[10px]">No screenshot</span>
						</div>
					{/if}
					<div class="absolute top-1.5 left-1.5 flex items-center gap-1">
						<Badge
							variant="outline"
							class="gap-1 border-border/60 bg-background/90 px-1.5 font-mono text-[10px] backdrop-blur"
						>
							<span class="size-1.5 rounded-full {STATUS_DOT[cls]}"></span>
							{s.http_status ?? '—'}
						</Badge>
						{#if cert === 'expired' || cert === 'self-signed'}
							<Badge
								variant="outline"
								class="gap-1 border-border/60 bg-background/90 px-1.5 text-[10px] text-destructive backdrop-blur"
							>
								<Lock class="size-2.5" />
								{cert}
							</Badge>
						{/if}
					</div>
					{#if s.http_url}
						<a
							href={s.http_url}
							target="_blank"
							rel="noreferrer noopener"
							onclick={stop}
							class="absolute top-1.5 right-1.5 flex size-6 items-center justify-center rounded-md border border-border/60 bg-background/90 text-muted-foreground opacity-0 backdrop-blur transition-opacity group-hover:opacity-100 hover:text-foreground focus-visible:opacity-100"
							aria-label="Open {s.name} in browser"
						>
							<ExternalLink class="size-3" />
						</a>
					{/if}
				</div>
				<div class="flex flex-col gap-1 p-2.5">
					<span class="truncate font-mono text-xs font-medium">{s.name}</span>
					<span class="truncate text-[11px] text-muted-foreground">
						{s.page_title ?? (s.http_status ? 'No page title' : 'No HTTP service')}
					</span>
					{#if s.tech.length || s.is_cdn}
						<div class="mt-0.5 flex flex-wrap gap-1">
							{#if s.is_cdn}
								<Badge variant="info" class="px-1 text-[9px] font-normal">
									<TechIcon name={s.cdn_name ?? ''} class="size-2.5" />
									{s.cdn_name ?? 'CDN'}
								</Badge>
							{/if}
							{#each s.tech.slice(0, MAX_TECH) as t (t)}
								<Badge variant="outline" class="px-1 text-[9px] font-normal">
									<TechIcon name={t} class="size-2.5" />
									{t}
								</Badge>
							{/each}
							{#if s.tech.length > MAX_TECH}
								<Badge variant="outline" class="px-1 text-[9px] font-normal text-muted-foreground">
									+{s.tech.length - MAX_TECH}
								</Badge>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/each}
	</div>
</ScrollArea>
