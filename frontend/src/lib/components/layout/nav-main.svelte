<script lang="ts" module>
	import type { IconComponent } from '$lib/config/icons';

	export interface NavBadge {
		count: number;
		live?: boolean;
	}

	export interface NavItem {
		title: string;
		url: string;
		icon?: IconComponent;
		badge?: NavBadge | null;
		items?: { title: string; url: string }[];
	}

	export interface NavGroup {
		label: string | null;
		items: NavItem[];
	}
</script>

<script lang="ts">
	import { navAccent } from '$lib/config/nav-accents';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import { page } from '$app/state';
	import { SvelteSet } from 'svelte/reactivity';

	let { groups }: { groups: NavGroup[] } = $props();

	const isActive = (url: string) => {
		const path = page.url.pathname;
		const base = url.split('?')[0];
		return path === base || path.startsWith(base + '/');
	};

	const hasActiveChild = (items?: { url: string }[]) => {
		return items?.some((item) => isActive(item.url)) ?? false;
	};

	const openItems = new SvelteSet<string>();
	$effect(() => {
		for (const group of groups) {
			for (const item of group.items) {
				if (hasActiveChild(item.items)) openItems.add(item.title);
			}
		}
	});
	const toggleOpen = (title: string, open: boolean) => {
		if (open) openItems.add(title);
		else openItems.delete(title);
	};
</script>

{#snippet link(item: NavItem, props: Record<string, unknown>)}
	{@const active = isActive(item.url)}
	{@const accent = active ? navAccent(item.url) : null}
	<a href={item.url} {...props}>
		{#if item.icon}
			<item.icon class="size-4" style={accent ? `color: ${accent}` : undefined} />
		{/if}
		<span>{item.title}</span>
	</a>
{/snippet}

{#snippet badge(b: NavBadge)}
	<Sidebar.MenuBadge
		class="gap-1 rounded-full bg-info/10 px-1.5 font-mono text-[10px] font-semibold text-info peer-hover/menu-button:text-info peer-data-[active=true]/menu-button:text-info"
	>
		{#if b.live}
			<span class="size-1.5 animate-pulse rounded-full bg-info"></span>
		{/if}
		{b.count}
	</Sidebar.MenuBadge>
{/snippet}

{#each groups as group, groupIndex (group.label ?? groupIndex)}
	<Sidebar.Group class={groupIndex > 0 ? 'pt-0' : undefined}>
		{#if group.label}
			<Sidebar.GroupLabel
				class="h-7 px-2 text-[10px] font-semibold tracking-[0.1em] text-muted-foreground/60 uppercase"
			>
				{group.label}
			</Sidebar.GroupLabel>
		{/if}
		<Sidebar.Menu>
			{#each group.items as item (item.title)}
				{#if item.items && item.items.length > 0}
					<Collapsible.Root
						open={openItems.has(item.title)}
						onOpenChange={(open) => toggleOpen(item.title, open)}
						class="group/collapsible"
					>
						{#snippet child({ props })}
							<Sidebar.MenuItem {...props}>
								<Sidebar.MenuButton tooltipContent={item.title} isActive={isActive(item.url)}>
									{#snippet child({ props })}
										{@render link(item, props)}
									{/snippet}
								</Sidebar.MenuButton>
								<Collapsible.Trigger>
									{#snippet child({ props })}
										<Sidebar.MenuAction
											{...props}
											class="transition-transform data-[state=open]:rotate-90"
											aria-label={openItems.has(item.title)
												? `Collapse ${item.title}`
												: `Expand ${item.title}`}
										>
											<ChevronRightIcon class="size-4" />
										</Sidebar.MenuAction>
									{/snippet}
								</Collapsible.Trigger>
								<Collapsible.Content>
									<Sidebar.MenuSub>
										{#each item.items as subItem (subItem.title)}
											<Sidebar.MenuSubItem>
												<Sidebar.MenuSubButton isActive={isActive(subItem.url)}>
													{#snippet child({ props })}
														<a href={subItem.url} {...props}>
															<span>{subItem.title}</span>
														</a>
													{/snippet}
												</Sidebar.MenuSubButton>
											</Sidebar.MenuSubItem>
										{/each}
									</Sidebar.MenuSub>
								</Collapsible.Content>
							</Sidebar.MenuItem>
						{/snippet}
					</Collapsible.Root>
				{:else}
					<Sidebar.MenuItem>
						<Sidebar.MenuButton tooltipContent={item.title} isActive={isActive(item.url)}>
							{#snippet child({ props })}
								{@render link(item, props)}
							{/snippet}
						</Sidebar.MenuButton>
						{#if item.badge}
							{@render badge(item.badge)}
						{/if}
					</Sidebar.MenuItem>
				{/if}
			{/each}
		</Sidebar.Menu>
	</Sidebar.Group>
{/each}
