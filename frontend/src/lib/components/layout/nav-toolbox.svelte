<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import Terminal from 'lucide-svelte/icons/terminal';
	import type { Component } from 'svelte';

	interface ToolboxItem {
		title: string;
		icon: Component;
		action: string;
	}

	let { items }: { items: ToolboxItem[] } = $props();

	const sidebar = useSidebar();

	function handleToolAction(action: string) {
		// Dispatch custom event or call a handler
		// TODO: Implement tool modals/panels
		console.log('Tool action:', action);

		window.dispatchEvent(new CustomEvent('toolbox-action', { detail: { action } }));
	}
</script>

<Sidebar.Group>
	<Sidebar.GroupLabel>Toolbox</Sidebar.GroupLabel>
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Sidebar.MenuButton {...props} tooltipContent="Command Center">
							<Terminal class="size-4" />
							<span>Command Center</span>
						</Sidebar.MenuButton>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content
					class="w-48 rounded-lg"
					side={sidebar.isMobile ? 'bottom' : 'right'}
					align="start"
					sideOffset={4}
				>
					<DropdownMenu.Label class="text-xs text-muted-foreground">Tools</DropdownMenu.Label>
					{#each items as item (item.action)}
						<DropdownMenu.Item onSelect={() => handleToolAction(item.action)} class="gap-2">
							<item.icon class="size-4 text-muted-foreground" />
							<span>{item.title}</span>
						</DropdownMenu.Item>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
</Sidebar.Group>