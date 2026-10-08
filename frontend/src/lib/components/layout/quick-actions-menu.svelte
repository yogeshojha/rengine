<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { mergeProps } from 'bits-ui';
	import Hint from '$lib/components/hint.svelte';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import Plus from '@lucide/svelte/icons/plus';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Cog from '@lucide/svelte/icons/cog';
	import Layers from '@lucide/svelte/icons/layers';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import { ORG_DOMAINS_ICON as OrgIcon, ORG_DOMAINS_TOOL } from '$lib/config/toolbox';

	let { onAddTarget }: { onAddTarget: () => void } = $props();
</script>

<DropdownMenu.Root>
	<Hint text="Create">
		{#snippet child(hintProps)}
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...mergeProps(hintProps, props)} variant="ghost" size="icon" aria-label="Create">
						<Plus class="h-4 w-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
		{/snippet}
	</Hint>
	<DropdownMenu.Content align="end" class="w-56">
		<DropdownMenu.Label>Create</DropdownMenu.Label>
		<DropdownMenu.Separator />
		<DropdownMenu.Item onclick={onAddTarget}>
			<Crosshair class="h-4 w-4" />
			Add target
		</DropdownMenu.Item>
		<DropdownMenu.Separator />
		<DropdownMenu.Label class="text-xs text-muted-foreground">Discover</DropdownMenu.Label>
		<DropdownMenu.Item onclick={() => toolbox.open({ value: '', tool: ORG_DOMAINS_TOOL })}>
			<OrgIcon class="h-4 w-4" />
			Domains by organization
		</DropdownMenu.Item>
		<DropdownMenu.Separator />
		<DropdownMenu.Label class="text-xs text-muted-foreground">Automation</DropdownMenu.Label>
		<DropdownMenu.Item onclick={() => goto(ROUTES.newEngine())}>
			<Cog class="h-4 w-4" />
			New engine
		</DropdownMenu.Item>
		<DropdownMenu.Item onclick={() => goto(ROUTES.newContext())}>
			<Layers class="h-4 w-4" />
			New context
		</DropdownMenu.Item>
	</DropdownMenu.Content>
</DropdownMenu.Root>
