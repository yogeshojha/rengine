<script lang="ts">
	import ImageOff from '@lucide/svelte/icons/image-off';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { screenshotUrl } from '$lib/utilities/media';
	import { claimHover, releaseHover } from '$lib/utilities/hover-exclusive';

	interface Props {
		path: string | null | undefined;
		alt?: string;
		class?: string;
		interactive?: boolean;
		preview?: boolean;
	}

	let {
		path,
		alt = 'screenshot',
		class: className = 'h-12 w-20',
		interactive = true,
		preview = false
	}: Props = $props();

	let failed = $state(false);
	$effect(() => {
		void path;
		failed = false;
	});
	let url = $derived(failed ? null : screenshotUrl(path));
	const stop = (e: Event) => e.stopPropagation();

	let hoverOpen = $state(false);
	const closeSelf = () => (hoverOpen = false);
	$effect(() => {
		if (hoverOpen) claimHover(closeSelf);
		else releaseHover(closeSelf);
	});
</script>

{#snippet thumb(src: string, cls: string)}
	<Dialog.Trigger
		onclick={stop}
		class="block cursor-zoom-in overflow-hidden rounded border border-border bg-muted {cls}"
	>
		<img
			{src}
			{alt}
			loading="lazy"
			onerror={() => (failed = true)}
			class="h-full w-full object-cover object-top"
		/>
	</Dialog.Trigger>
{/snippet}

{#snippet lightbox(src: string)}
	<Dialog.Content class="max-w-5xl">
		<Dialog.Title class="sr-only">Screenshot of {alt}</Dialog.Title>
		<img {src} {alt} class="max-h-[80vh] w-full rounded object-contain" />
	</Dialog.Content>
{/snippet}

{#if url && interactive && preview}
	<Dialog.Root>
		<HoverCard.Root bind:open={hoverOpen} openDelay={220} closeDelay={80}>
			<HoverCard.Trigger>
				{#snippet child({ props })}
					<span {...props} class="block {className}">
						{@render thumb(url, 'h-full w-full')}
					</span>
				{/snippet}
			</HoverCard.Trigger>
			<HoverCard.Content side="right" align="start" class="w-[28rem] overflow-hidden p-0">
				<img
					src={url}
					{alt}
					onerror={() => (failed = true)}
					class="block max-h-[26rem] w-full bg-muted object-cover object-top"
				/>
			</HoverCard.Content>
		</HoverCard.Root>
		{@render lightbox(url)}
	</Dialog.Root>
{:else if url && interactive}
	<Dialog.Root>
		{@render thumb(url, className)}
		{@render lightbox(url)}
	</Dialog.Root>
{:else if url}
	<div class="overflow-hidden rounded border border-border bg-muted {className}">
		<img
			src={url}
			{alt}
			loading="lazy"
			onerror={() => (failed = true)}
			class="h-full w-full object-cover object-top"
		/>
	</div>
{:else}
	<div
		class="flex items-center justify-center rounded border border-dashed border-border text-muted-foreground {className}"
	>
		<ImageOff class="size-4" />
	</div>
{/if}
