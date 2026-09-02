<script lang="ts">
	import { navAccent } from '$lib/config/nav-accents';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import { page } from '$app/stores';
	import type { Component } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';

	type NavItem = {
		title: string;
		url: string;
		icon?: Component;
		items?: {
			title: string;
			url: string;
		}[];
	};

	type NavGroup = {
		label: string | null;
		items: NavItem[];
	};

	let { groups }: { groups: NavGroup[] } = $props();

	const isActive = (url: string) => {
		return $page.url.pathname === url || $page.url.pathname.startsWith(url + '/');
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

{#each groups as group, groupIndex (group.label ?? groupIndex)}
	<Sidebar.Group>
		{#if group.label}
			<Sidebar.GroupLabel
				class="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-medium px-2"
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
										<a href={item.url} {...props}>
											{#if item.icon}
												<item.icon
													class="size-4"
													style={isActive(item.url) && navAccent(item.url)
														? `color: ${navAccent(item.url)}`
														: undefined}
												/>
											{/if}
											<span>{item.title}</span>
										</a>
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
								<a href={item.url} {...props}>
									{#if item.icon}
										<item.icon
											class="size-4"
											style={isActive(item.url) && navAccent(item.url)
												? `color: ${navAccent(item.url)}`
												: undefined}
										/>
									{/if}
									<span>{item.title}</span>
								</a>
							{/snippet}
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
				{/if}
			{/each}
		</Sidebar.Menu>
	</Sidebar.Group>
{/each}
