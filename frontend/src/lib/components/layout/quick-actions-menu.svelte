<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import Hint from '$lib/components/hint.svelte';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import Plus from '@lucide/svelte/icons/plus';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Building from '@lucide/svelte/icons/building';
	import Cog from '@lucide/svelte/icons/cog';
	import Layers from '@lucide/svelte/icons/layers';

	let { onAddTarget }: { onAddTarget: () => void } = $props();
</script>

<Hint text="Quick actions">
	{#snippet child(hintProps)}
		<span {...hintProps} class="inline-flex">
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon">
							<Plus class="h-4 w-4" />
							<span class="sr-only">Quick actions</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56">
					<DropdownMenu.Label>Create</DropdownMenu.Label>
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={onAddTarget}>
						<Crosshair class="mr-2 h-4 w-4" />
						Add target
					</DropdownMenu.Item>
					<DropdownMenu.Item disabled class="justify-between">
						<span class="flex items-center">
							<Building class="mr-2 h-4 w-4" />
							Add organization
						</span>
						<Badge variant="secondary" class="text-[10px]">Soon</Badge>
					</DropdownMenu.Item>
					<DropdownMenu.Separator />
					<DropdownMenu.Label class="text-xs text-muted-foreground">Automation</DropdownMenu.Label>
					<DropdownMenu.Item onclick={() => goto(ROUTES.engines)}>
						<Cog class="mr-2 h-4 w-4" />
						New scan engine
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => goto(ROUTES.contexts)}>
						<Layers class="mr-2 h-4 w-4" />
						New scan context
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</span>
	{/snippet}
</Hint>
