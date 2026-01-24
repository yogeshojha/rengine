<script lang="ts">
	import { page } from '$app/stores';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import ChevronRight from 'lucide-svelte/icons/chevron-right';
	import type { Component } from 'svelte';

	interface NavItem {
		title: string;
		url: string;
		icon: Component;
		items?: { title: string; url: string }[];
	}

	let { items }: { items: NavItem[] } = $props();

	function isActive(url: string): boolean {
		return $page.url.pathname === url || $page.url.pathname.startsWith(url + '/');
	}

	function isGroupActive(item: NavItem): boolean {
		if (isActive(item.url)) return true;
		return item.items?.some((sub) => isActive(sub.url)) ?? false;
	}
</script>

<Sidebar.Group>
	<Sidebar.GroupLabel>Navigation</Sidebar.GroupLabel>
	<Sidebar.Menu>
		{#each items as item (item.title)}
			{#if item.items && item.items.length > 0}
				<!-- Collapsible menu item -->
				<Collapsible.Root open={isGroupActive(item)} class="group/collapsible">
					{#snippet child({ props })}
						<Sidebar.MenuItem {...props}>
							<Collapsible.Trigger>
								{#snippet child({ props: triggerProps })}
									<Sidebar.MenuButton
										{...triggerProps}
										tooltipContent={item.title}
										class={isGroupActive(item) ? 'bg-sidebar-accent' : ''}
									>
										<item.icon class="size-4" />
										<span>{item.title}</span>
										<ChevronRight
											class="ms-auto size-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90"
										/>
									</Sidebar.MenuButton>
								{/snippet}
							</Collapsible.Trigger>
							<Collapsible.Content>
								<Sidebar.MenuSub>
									{#each item.items as subItem (subItem.title)}
										<Sidebar.MenuSubItem>
											<Sidebar.MenuSubButton>
												{#snippet child({ props: subProps })}
													
														href={subItem.url}
														{...subProps}
														class={isActive(subItem.url) ? 'bg-sidebar-accent' : ''}
													>
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
				<!-- Simple menu item -->
				<Sidebar.MenuItem>
					<Sidebar.MenuButton tooltipContent={item.title} class={isActive(item.url) ? 'bg-sidebar-accent' : ''}>
						{#snippet child({ props })}
							<a href={item.url} {...props}>
								<item.icon class="size-4" />
								<span>{item.title}</span>
							</a>
						{/snippet}
					</Sidebar.MenuButton>
				</Sidebar.MenuItem>
			{/if}
		{/each}
	</Sidebar.Menu>
</Sidebar.Group>