<script lang="ts">
	import Filter from '@lucide/svelte/icons/filter';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Layers from '@lucide/svelte/icons/layers';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { cn } from '$lib/utils';

	interface Props {
		count: number;
		title: string;
		load: () => Promise<string[]>;
		onHost?: (name: string) => void;
		onFilter?: () => void;
		class?: string;
	}

	let { count, title, load, onHost, onFilter, class: className }: Props = $props();

	let open = $state(false);
	let hosts = $state<string[] | null>(null);
	let errored = $state(false);

	$effect(() => {
		void title;
		hosts = null;
		errored = false;
	});
	$effect(() => {
		if (!open || hosts || errored) return;
		load()
			.then((h) => (hosts = h))
			.catch(() => (errored = true));
	});

	const stop = (e: Event) => e.stopPropagation();
	function pick(h: string) {
		open = false;
		onHost?.(h);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger
		openOnHover
		openDelay={240}
		closeDelay={140}
		onclick={stop}
		onkeydown={stop}
		class={cn(
			'inline-flex h-5 shrink-0 cursor-pointer items-center gap-0.5 rounded-sm border border-border px-1 text-[10px] text-muted-foreground tabular-nums hover:bg-accent hover:text-foreground',
			className
		)}
		aria-label={title}
	>
		<Layers class="size-2.5" />
		{count}
	</Popover.Trigger>
	<Popover.Content class="w-72 p-0" align="start" onclick={stop}>
		<div class="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
			<span class="truncate text-xs font-medium" {title}>{title}</span>
			{#if onFilter}
				<Button
					variant="ghost"
					size="sm"
					class="h-6 shrink-0 text-xs"
					onclick={() => {
						open = false;
						onFilter();
					}}
				>
					<Filter data-icon="inline-start" /> Filter
				</Button>
			{/if}
		</div>
		<ScrollArea class={(hosts?.length ?? 0) > 8 ? 'h-64' : ''}>
			<div class="p-1">
				{#if errored}
					<p class="px-2 py-3 text-xs text-muted-foreground">Hosts could not be loaded.</p>
				{:else if hosts === null}
					<div class="flex flex-col gap-1 p-1">
						<Skeleton class="h-6 w-full" />
						<Skeleton class="h-6 w-5/6" />
						<Skeleton class="h-6 w-2/3" />
					</div>
				{:else}
					<ul class="flex flex-col">
						{#each hosts as h (h)}
							<li>
								<button
									type="button"
									class="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left font-mono text-xs hover:bg-accent"
									onclick={() => pick(h)}
								>
									<span class="truncate">{h}</span>
									<ChevronRight class="size-3 shrink-0 text-muted-foreground" />
								</button>
							</li>
						{/each}
					</ul>
					{#if hosts.length < count}
						<p class="px-2 pt-2 pb-1 text-[11px] text-muted-foreground">
							Showing {hosts.length} of {count}. Use Filter for the full list.
						</p>
					{/if}
				{/if}
			</div>
		</ScrollArea>
	</Popover.Content>
</Popover.Root>
