<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { LOCKED_NAV_ITEMS, useSidebarNav } from './sidebar-nav.svelte';
	import type { NavGroup } from './nav-main.svelte';
	import { sidebarLayout } from '$lib/stores/sidebar-layout.svelte';
	import { cn } from '$lib/utils';
	import { untrack } from 'svelte';

	const FOOTER_LABEL = 'Bottom';

	const nav = useSidebarNav();

	$effect(() => {
		untrack(() => sidebarLayout.load());
	});

	const columns = $derived([nav.all.slice(0, 2), nav.all.slice(2)]);
	const footer = $derived(nav.all.at(-1));
</script>

{#snippet group(g: NavGroup, first: boolean)}
	<div class={cn('flex flex-col', !first && 'mt-2 border-t pt-2')}>
		{#if g.label || g === footer}
			<p
				class="flex h-7 items-center px-1.5 text-2xs font-semibold tracking-[0.1em] text-muted-foreground/60 uppercase"
			>
				{g.label ?? FOOTER_LABEL}
			</p>
		{/if}
		{#each g.items as item (item.id)}
			{@const locked = LOCKED_NAV_ITEMS.includes(item.id)}
			{@const shown = !sidebarLayout.hidden(item.id)}
			<label
				for="nav-{item.id}"
				class={cn(
					'flex h-8 items-center gap-2.5 rounded-md px-1.5 text-sm',
					!locked && 'cursor-pointer hover:bg-muted/60'
				)}
			>
				<Checkbox
					id="nav-{item.id}"
					checked={shown}
					disabled={locked}
					onCheckedChange={(v) => sidebarLayout.set(item.id, v === true)}
				/>
				{#if item.icon}
					<item.icon class={cn('size-4', !shown && 'text-muted-foreground')} />
				{/if}
				<span class={cn('flex-1 truncate', !shown && 'text-muted-foreground')}>{item.title}</span>
				{#if locked}
					<span class="text-2xs text-muted-foreground">Always shown</span>
				{/if}
			</label>
			{#each item.items ?? [] as child (child.id)}
				{@const childShown = shown && !sidebarLayout.hidden(child.id)}
				<label
					for="nav-{child.id}"
					class={cn(
						'ms-6.5 flex h-7 items-center gap-2.5 rounded-md px-1.5 text-sm',
						shown ? 'cursor-pointer hover:bg-muted/60' : 'opacity-50'
					)}
				>
					<Checkbox
						id="nav-{child.id}"
						checked={childShown}
						disabled={!shown}
						onCheckedChange={(v) => sidebarLayout.set(child.id, v === true)}
					/>
					<span class={cn('flex-1 truncate', !childShown && 'text-muted-foreground')}>
						{child.title}
					</span>
				</label>
			{/each}
		{/each}
	</div>
{/snippet}

<div class="grid gap-x-8 gap-y-2 sm:grid-cols-2">
	{#each columns as column, c (c)}
		<div class="flex min-w-0 flex-col">
			{#each column as g, i (g.label ?? `group-${c}-${i}`)}
				{@render group(g, i === 0)}
			{/each}
		</div>
	{/each}
</div>
