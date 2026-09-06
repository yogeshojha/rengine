<script lang="ts">
	import { onDestroy } from 'svelte';
	import { cn } from '$lib/utils.js';
	import { releaseCanvas, renderPage, type PageSize } from '$lib/utilities/pdf';
	import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

	let {
		doc,
		number,
		size,
		scale,
		active,
		class: className
	}: {
		doc: PDFDocumentProxy;
		number: number;
		size: PageSize;
		scale: number;
		active: boolean;
		class?: string;
	} = $props();

	let canvas = $state<HTMLCanvasElement | null>(null);
	let painted = $state(false);
	let task: RenderTask | null = null;
	let token = 0;

	const width = $derived(Math.round(size.width * scale));
	const height = $derived(Math.round(size.height * scale));

	$effect(() => {
		const element = canvas;
		const at = scale;
		const wanted = active;
		if (!element) return;

		task?.cancel();
		task = null;

		if (!wanted) {
			releaseCanvas(element);
			painted = false;
			return;
		}

		const mine = ++token;
		void (async () => {
			const page = await doc.getPage(number);
			if (mine !== token) return;
			const started = renderPage(page, element, at);
			task = started;
			try {
				await started.promise;
				if (mine === token) painted = true;
			} catch {}
		})();

		return () => {
			token++;
		};
	});

	onDestroy(() => task?.cancel());
</script>

<div
	class={cn('relative overflow-hidden bg-white', className)}
	style="width:{width}px;height:{height}px"
>
	<canvas bind:this={canvas} class="block" class:invisible={!painted} aria-label="Page {number}"
	></canvas>
</div>
