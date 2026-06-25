<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import Plus from '@lucide/svelte/icons/plus';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Building from '@lucide/svelte/icons/building';
	import Cog from '@lucide/svelte/icons/cog';
	import Layers from '@lucide/svelte/icons/layers';

	let { onAddTarget }: { onAddTarget: () => void } = $props();
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="ghost" size="icon" title="Quick actions">
				<Plus class="h-4 w-4" />
				<span class="sr-only">Quick Actions</span>
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="w-56">
		<DropdownMenu.Label>Create New</DropdownMenu.Label>
		<DropdownMenu.Separator />
		<DropdownMenu.Item onclick={onAddTarget}>
			<Crosshair class="mr-2 h-4 w-4" />
			Add Target
		</DropdownMenu.Item>
		<DropdownMenu.Item disabled class="justify-between">
			<span class="flex items-center">
				<Building class="mr-2 h-4 w-4" />
				Add Organization
			</span>
			<Badge variant="secondary" class="text-[10px]">Soon</Badge>
		</DropdownMenu.Item>
		<DropdownMenu.Separator />
		<DropdownMenu.Label class="text-xs text-muted-foreground">Automation</DropdownMenu.Label>
		<DropdownMenu.Item onclick={() => goto(ROUTES.engines)}>
			<Cog class="mr-2 h-4 w-4" />
			New Scan Engine
		</DropdownMenu.Item>
		<DropdownMenu.Item onclick={() => goto(ROUTES.contexts)}>
			<Layers class="mr-2 h-4 w-4" />
			New Scan Context
		</DropdownMenu.Item>
	</DropdownMenu.Content>
</DropdownMenu.Root>
