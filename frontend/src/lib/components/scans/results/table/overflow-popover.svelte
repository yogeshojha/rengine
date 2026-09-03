<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Popover from '$lib/components/ui/popover';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import TechIcon from '../tech-icon.svelte';
	import { cn } from '$lib/utils';

	interface Props {
		items: string[];
		shown: number;
		label: string;
		mono?: boolean;
		icons?: boolean;
		onSelect?: (value: string) => void;
		class?: string;
	}

	let {
		items,
		shown,
		label,
		mono = false,
		icons = false,
		onSelect,
		class: className
	}: Props = $props();

	let open = $state(false);
	let hidden = $derived(Math.max(0, items.length - shown));
	const stop = (e: Event) => e.stopPropagation();

	function pick(v: string) {
		open = false;
		onSelect?.(v);
	}
</script>

{#if hidden > 0}
	<Popover.Root bind:open>
		<Popover.Trigger
			openOnHover
			openDelay={160}
			closeDelay={140}
			onclick={stop}
			onkeydown={stop}
			class={cn(
				'inline-flex h-5 cursor-pointer items-center rounded-sm border border-border px-1 text-[10px] text-muted-foreground tabular-nums hover:bg-accent hover:text-foreground',
				className
			)}
			aria-label="Show all {items.length} {label}"
		>
			+{hidden}
		</Popover.Trigger>
		<Popover.Content class="w-64 p-0" align="start" onclick={stop}>
			<div class="border-b border-border px-3 py-2 text-xs font-medium">
				{items.length}
				{label}
			</div>
			<ScrollArea class={items.length > 8 ? 'h-64' : ''}>
				<ul class="flex flex-col p-1">
					{#each items as item (item)}
						<li>
							{#if onSelect}
								<button
									type="button"
									class="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent {mono
										? 'font-mono'
										: ''}"
									onclick={() => pick(item)}
								>
									<span class="flex min-w-0 items-center gap-1.5">
										{#if icons}<span class="flex w-3 shrink-0 justify-center">
												<TechIcon name={item} />
											</span>{/if}
										<span class="truncate">{item}</span>
									</span>
									<ChevronRight class="size-3 shrink-0 text-muted-foreground" />
								</button>
							{:else}
								<span
									class="flex items-center gap-1.5 px-2 py-1.5 text-xs {mono ? 'font-mono' : ''}"
								>
									{#if icons}<span class="flex w-3 shrink-0 justify-center">
											<TechIcon name={item} />
										</span>{/if}
									<span class="truncate">{item}</span>
								</span>
							{/if}
						</li>
					{/each}
				</ul>
			</ScrollArea>
		</Popover.Content>
	</Popover.Root>
{/if}
