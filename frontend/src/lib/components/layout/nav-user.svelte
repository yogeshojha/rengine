<script lang="ts">
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import UserIcon from '@lucide/svelte/icons/user';
	import Info from '@lucide/svelte/icons/info';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import LogOutIcon from '@lucide/svelte/icons/log-out';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { VERSION } from '$lib/version.js';
	import { Button } from '$lib/components/ui/button/index.js';

	let { user }: { user: { name: string; email: string; is_superuser: boolean } } = $props();
	const sidebar = useSidebar();

	let aboutDialogOpen = $state(false);

	// Generate initials from name
	const getInitials = (name: string) => {
		return name
			.split(' ')
			.map((n) => n[0])
			.join('')
			.toUpperCase()
			.slice(0, 2);
	};
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
						{...props}
					>
						<Avatar.Root class="size-8 rounded-lg">
							<Avatar.Fallback class="rounded-lg bg-primary text-primary-foreground">
								{getInitials(user.name)}
							</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{user.name}</span>
							<span class="truncate text-xs">{user.email}</span>
						</div>
						<ChevronsUpDownIcon class="ms-auto size-4" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
				side={sidebar.isMobile ? 'bottom' : 'right'}
				align="end"
				sideOffset={4}
			>
				<DropdownMenu.Label class="p-0 font-normal">
					<div class="flex items-center gap-2 px-1 py-1.5 text-start text-sm">
						<Avatar.Root class="size-8 rounded-lg">
							<Avatar.Fallback class="rounded-lg bg-primary text-primary-foreground">
								{getInitials(user.name)}
							</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{user.name}</span>
							<span class="truncate text-xs">{user.email}</span>
							{#if user.is_superuser}
								<Badge variant="secondary" class="bg-blue-500 text-white dark:bg-blue-600 mt-1">
									<ShieldIcon class="w-3 h-3 mr-1" />
									Admin
								</Badge>
							{/if}
						</div>
					</div>
				</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.Group>
					<DropdownMenu.Item>
						<UserIcon class="size-4" />
						Profile
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => (aboutDialogOpen = true)}>
						<Info class="size-4" />
						About reNgine
					</DropdownMenu.Item>
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>
					<LogOutIcon class="size-4" />
					Log out
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>

<!-- About Dialog -->
<Dialog.Root bind:open={aboutDialogOpen}>
	<Dialog.Content>
		<Dialog.Header>
			<Dialog.Title>About reNgine</Dialog.Title>
			<Dialog.Description>Open Source Attack Surface Management Platform</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4 py-4">
			<div class="space-y-2">
				<h4 class="font-medium">Version</h4>
				<p class="text-sm text-muted-foreground">reNgine {VERSION}</p>
			</div>
			<div class="space-y-2">
				<h4 class="font-medium">GitHub</h4>
				<a
					href="https://github.com/yogeshojha/rengine"
					target="_blank"
					class="text-sm text-blue-500 hover:underline"
				>
					github.com/yogeshojha/rengine
				</a>
			</div>
			<div class="space-y-2">
				<h4 class="font-medium">Wiki</h4>
				<a
					href="https://rengine.wiki"
					target="_blank"
					class="text-sm text-blue-500 hover:underline"
				>
					rengine.wiki
				</a>
			</div>
			<div class="space-y-2">
				<h4 class="font-medium">License</h4>
				<p class="text-sm text-muted-foreground">GNU General Public License v3.0</p>
			</div>
		</div>
		<Dialog.Footer class="flex justify-between">
			<Button variant="outline">
				Check for Updates
			</Button>
			<Button variant="ghost" onclick={() => aboutDialogOpen = false}>
				Close
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
