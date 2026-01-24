<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import Zap from 'lucide-svelte/icons/zap';
	import type { Component } from 'svelte';

	interface QuickAction {
		title: string;
		icon: Component;
		action: string;
	}

	let { actions }: { actions: QuickAction[] } = $props();

	const sidebar = useSidebar();

	function handleQuickAction(action: string) {
		console.log('Quick action:', action);
		window.dispatchEvent(new CustomEvent('quick-action', { detail: { action } }));
	}
</script>

<Sidebar.Group>
	<Sidebar.GroupLabel>Quick Actions</Sidebar.GroupLabel>
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Sidebar.MenuButton {...props} tooltipContent="Quick Actions">
							<Zap class="size-4" />
							<span>Quick Menu</span>
						</Sidebar.MenuButton>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content
					class="w-48 rounded-lg"
					side={sidebar.isMobile ? 'bottom' : 'right'}
					align="start"
					sideOffset={4}
				>
					<DropdownMenu.Label class="text-xs text-muted-foreground">Create</DropdownMenu.Label>
					{#each actions as action (action.action)}
						<DropdownMenu.Item onSelect={() => handleQuickAction(action.action)} class="gap-2">
							<action.icon class="size-4 text-muted-foreground" />
							<span>{action.title}</span>
						</DropdownMenu.Item>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
</Sidebar.Group>