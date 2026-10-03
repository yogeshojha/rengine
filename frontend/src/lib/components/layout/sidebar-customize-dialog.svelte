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
		class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Customize sidebar</Dialog.Title>
			<Dialog.Description>Applies to this account in this browser</Dialog.Description>
		</Dialog.Header>
		<ScrollArea class="min-h-0 flex-1">
			<div class="px-6 py-5">
				<SidebarItems />
			</div>
		</ScrollArea>
		<Dialog.Footer class="border-t px-6 py-4">
			{#if sidebarLayout.customized}
				<Button variant="outline" onclick={() => sidebarLayout.reset()}>Show all</Button>
			{/if}
			<Button onclick={() => (open = false)}>Done</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
