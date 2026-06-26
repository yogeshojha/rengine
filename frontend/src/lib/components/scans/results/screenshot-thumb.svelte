<script lang="ts">
	import ImageOff from '@lucide/svelte/icons/image-off';
	import * as Dialog from '$lib/components/ui/dialog';
	import { screenshotUrl } from '$lib/utilities/media';

	interface Props {
		path: string | null | undefined;
		alt?: string;
		class?: string;
		interactive?: boolean;
	}

	let {
		path,
		alt = 'screenshot',
		class: className = 'h-12 w-20',
		interactive = true
	}: Props = $props();

	let url = $derived(screenshotUrl(path));
</script>

{#if url && interactive}
	<Dialog.Root>
		<Dialog.Trigger
			onclick={(e) => e.stopPropagation()}
			class="block cursor-zoom-in overflow-hidden rounded border border-border bg-muted {className}"
		>
			<img src={url} {alt} loading="lazy" class="h-full w-full object-cover object-top" />
		</Dialog.Trigger>
		<Dialog.Content class="max-w-5xl">
			<Dialog.Title class="sr-only">Screenshot of {alt}</Dialog.Title>
			<img src={url} {alt} class="max-h-[80vh] w-full rounded object-contain" />
		</Dialog.Content>
	</Dialog.Root>
{:else if url}
	<div class="overflow-hidden rounded border border-border bg-muted {className}">
		<img src={url} {alt} loading="lazy" class="h-full w-full object-cover object-top" />
	</div>
{:else}
	<div
		class="flex items-center justify-center rounded border border-dashed border-border text-muted-foreground {className}"
	>
		<ImageOff class="size-4" />
	</div>
{/if}
