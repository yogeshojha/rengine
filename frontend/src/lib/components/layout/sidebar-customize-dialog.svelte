<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import SidebarItems from './sidebar-items.svelte';
	import { sidebarLayout } from '$lib/stores/sidebar-layout.svelte';

	let { open = $bindable(false) }: { open?: boolean } = $props();
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		class="flex max-h-[90vh] flex-col gap-4 sm:max-w-2xl"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		<Dialog.Header>
			<Dialog.Title>Customize sidebar</Dialog.Title>
			<Dialog.Description>Applies to this account in this browser</Dialog.Description>
		</Dialog.Header>
		<ScrollArea class="-mx-2 min-h-0 flex-1 px-2">
			<SidebarItems />
		</ScrollArea>
		<Dialog.Footer class="border-t pt-4">
			{#if sidebarLayout.customized}
				<Button variant="ghost" onclick={() => sidebarLayout.reset()}>Show all</Button>
			{/if}
			<Button onclick={() => (open = false)}>Done</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
