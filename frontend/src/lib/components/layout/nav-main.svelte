<script lang="ts" module>
	import type { IconComponent } from '$lib/config/icons';

	export type NavBadgeTone = 'info' | 'muted' | 'attention';

	export interface NavBadge {
		label: string;
		live?: boolean;
		tone?: NavBadgeTone;
	}

	export interface NavChild {
		title: string;
		url: string;
		/** sibling routes this item stays lit for */
		match?: string[];
	}

	export interface NavItem extends NavChild {
		icon?: IconComponent;
		badge?: NavBadge | null;
		items?: NavChild[];
	}

	export interface NavGroup {
		label: string | null;
		items: NavItem[];
	}
</script>

<script lang="ts">
	import { cn } from '$lib/utils';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/context.svelte.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import { page } from '$app/state';
	import { SvelteMap } from 'svelte/reactivity';

	let { groups, class: className }: { groups: NavGroup[]; class?: string } = $props();

	const sidebar = useSidebar();

	const isActive = (url: string) => {
		const path = page.url.pathname;
		const base = url.split('?')[0];
		return path === base || path.startsWith(base + '/');
	};

	const childActive = (item: NavChild) => isActive(item.url) || (item.match ?? []).some(isActive);
	const branchActive = (item: NavItem) => item.items?.some(childActive) ?? false;

	// chevron overrides, dropped on every navigation
	const overrides = new SvelteMap<string, boolean>();
	$effect(() => {
		void page.url.pathname;
		overrides.clear();
	});
	const isOpen = (item: NavItem) => overrides.get(item.title) ?? branchActive(item);
	const railCollapsed = () => !sidebar.isMobile && sidebar.state === 'collapsed';
	const setOpen = (item: NavItem, open: boolean) => {
		if (railCollapsed()) {
			sidebar.setOpen(true);
			overrides.set(item.title, true);
			return;
		}
		overrides.set(item.title, open);
	};
</script>

{#snippet link(item: NavItem, props: Record<string, unknown>)}
	<a href={item.url} {...props}>
		{#if item.icon}
			<item.icon class="size-4" />
		{/if}
		<span>{item.title}</span>
	</a>
{/snippet}

{#snippet badge(b: NavBadge, offset: boolean)}
	{@const tone = b.tone ?? 'info'}
	<Sidebar.MenuBadge
		class={cn(
			'top-1 gap-1 rounded-full px-1.5 font-mono text-2xs font-semibold',
			offset && 'end-7',
			tone === 'info' &&
				'bg-info/10 text-info peer-hover/menu-button:text-info peer-data-[active=true]/menu-button:text-info',
			tone === 'attention' &&
				'bg-destructive/10 text-destructive peer-hover/menu-button:text-destructive peer-data-[active=true]/menu-button:text-destructive',
			tone === 'muted' && 'text-muted-foreground/70'
		)}
	>
		{#if b.live}
			<span class="size-1.5 animate-pulse rounded-full bg-info"></span>
		{/if}
		{b.label}
	</Sidebar.MenuBadge>
{/snippet}

{#each groups as group, groupIndex (group.label ?? groupIndex)}
	<Sidebar.Group class={cn(groupIndex > 0 && 'pt-0 group-data-[collapsible=icon]:pt-3', className)}>
		{#if group.label}
			<Sidebar.GroupLabel
				class="h-6 px-2 text-2xs font-semibold tracking-[0.1em] text-muted-foreground/60 uppercase"
			>
				{group.label}
			</Sidebar.GroupLabel>
		{/if}
		<Sidebar.Menu class="gap-0.5">
			{#each group.items as item (item.title)}
				{#if item.items && item.items.length > 0}
					<Collapsible.Root
						open={isOpen(item)}
						onOpenChange={(open) => setOpen(item, open)}
						class="group/collapsible"
					>
						{#snippet child({ props })}
							<Sidebar.MenuItem {...props}>
								<Collapsible.Trigger>
									{#snippet child({ props })}
										<Sidebar.MenuButton
											{...props}
											class="h-7"
											tooltipContent={item.title}
											isActive={railCollapsed() && branchActive(item)}
										>
											{#if item.icon}
												<item.icon class="size-4" />
											{/if}
											<span>{item.title}</span>
											<ChevronRightIcon
												class="ms-auto size-4 text-muted-foreground transition-transform group-data-[state=open]/collapsible:rotate-90"
											/>
										</Sidebar.MenuButton>
									{/snippet}
								</Collapsible.Trigger>
								{#if item.badge}
									{@render badge(item.badge, true)}
								{/if}
								<Collapsible.Content>
									<Sidebar.MenuSub class="gap-0.5">
										{#each item.items as subItem (subItem.title)}
											<Sidebar.MenuSubItem>
												<Sidebar.MenuSubButton isActive={childActive(subItem)}>
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
						<Sidebar.MenuButton
							class="h-7"
							tooltipContent={item.title}
							isActive={childActive(item)}
						>
							{#snippet child({ props })}
								{@render link(item, props)}
							{/snippet}
						</Sidebar.MenuButton>
						{#if item.badge}
							{@render badge(item.badge, false)}
						{/if}
					</Sidebar.MenuItem>
				{/if}
			{/each}
		</Sidebar.Menu>
	</Sidebar.Group>
{/each}
