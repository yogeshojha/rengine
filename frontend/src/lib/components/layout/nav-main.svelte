<script lang="ts">
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';

	type NavItem = {
		title: string;
		url: string;
		icon?: any;
		isActive?: boolean;
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
</script>

{#each groups as group, groupIndex (group.label ?? groupIndex)}
	<Sidebar.Group>
		{#if group.label}
			<Sidebar.GroupLabel class="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-medium px-2">
				{group.label}
			</Sidebar.GroupLabel>
		{/if}
		<Sidebar.Menu>
			{#each group.items as item (item.title)}
				{#if item.items && item.items.length > 0}
					<Collapsible.Root open={item.isActive} class="group/collapsible">
						{#snippet child({ props })}
							<Sidebar.MenuItem {...props}>
								<Collapsible.Trigger>
									{#snippet child({ props })}
										<Sidebar.MenuButton {...props} tooltipContent={item.title}>
											{#if item.icon}
												<item.icon class="size-4" />
											{/if}
											<span>{item.title}</span>
											<ChevronRightIcon
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
						<Sidebar.MenuButton tooltipContent={item.title}>
							{#snippet child({ props })}
								<a href={item.url} {...props}>
									{#if item.icon}
										<item.icon class="size-4" />
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
