<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import type { TripwireCatalog, TripwireTemplate } from '$lib/types/tripwire';
	import TemplateGrid from './template-grid.svelte';

	interface Props {
		open: boolean;
		catalog: TripwireCatalog | null;
		onOpenChange: (open: boolean) => void;
		onPick: (template: TripwireTemplate) => void;
	}

	let { open, catalog, onOpenChange, onPick }: Props = $props();
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		side="right"
		class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>Templates</Sheet.Title>
		</Sheet.Header>
		<ScrollArea class="min-h-0 flex-1">
			<div class="px-5 py-4">
				{#if catalog}
					<TemplateGrid
						templates={catalog.templates}
						groups={catalog.template_groups}
						columns="sm:grid-cols-2"
						onPick={(t) => {
							onPick(t);
							onOpenChange(false);
						}}
					/>
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>
