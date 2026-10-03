<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import type { SheetAction } from './sheet';
	import { externalHref } from '$lib/utilities/links';

	interface Props {
		actions: SheetAction[];
	}

	let { actions }: Props = $props();
</script>

{#if actions.length}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="outline" size="icon-sm" aria-label="More actions">
					<Ellipsis class="size-4" />
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-52">
			{#each actions as action (action.label)}
				{@const Icon = action.icon}
				{#if action.href}
					<DropdownMenu.Item>
						{#snippet child({ props })}
							<a
								{...props}
								href={externalHref(action.href)}
								target="_blank"
								rel="noopener noreferrer"
							>
								<Icon class="size-4" />
								{action.label}
							</a>
						{/snippet}
					</DropdownMenu.Item>
				{:else}
					<DropdownMenu.Item onSelect={() => action.run?.()}>
						<Icon class="size-4" />
						{action.label}
					</DropdownMenu.Item>
				{/if}
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}
