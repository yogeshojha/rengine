<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { visible } from '$lib/utilities/visible';
	import PdfPage from './pdf-page.svelte';
	import type { PageSize } from '$lib/utilities/pdf';
	import type { PDFDocumentProxy } from 'pdfjs-dist';

	const GUTTER = 40;
	const MAX_FIT = 1.35;
	const RENDER_MARGIN = '80% 0px';

	let {
		doc,
		sizes,
		fit,
		zoom,
		page = $bindable(1),
		scale = $bindable(1)
	}: {
		doc: PDFDocumentProxy;
		sizes: PageSize[];
		fit: 'width' | 'page' | null;
		zoom: number;
		page?: number;
		scale?: number;
	} = $props();

	let viewport = $state<HTMLElement | null>(null);
	let width = $state(0);
	let height = $state(0);
	const live = new SvelteSet<number>();
	let lastScale = 0;

	const base = $derived(sizes[0] ?? { width: 595, height: 842 });
	const fitWidth = $derived(
		width ? Math.min(Math.max((width - GUTTER * 2) / base.width, 0.1), MAX_FIT) : 1
	);
	const fitPage = $derived(height ? Math.max((height - GUTTER * 2) / base.height, 0.1) : 1);
	const effective = $derived(
		fit === 'width' ? fitWidth : fit === 'page' ? Math.min(fitWidth, fitPage) : zoom
	);

	$effect(() => {
		scale = effective;
	});

	$effect(() => {
		const root = viewport;
		const count = sizes.length;
		if (!root || !count) return;

		const ratios = new Array<number>(count).fill(0);
		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const number = Number((entry.target as HTMLElement).dataset.pdfPage);
					ratios[number - 1] = entry.intersectionRatio;
				}
				let best = 0;
				let bestRatio = 0;
				ratios.forEach((ratio, index) => {
					if (ratio > bestRatio + 0.01) {
						best = index + 1;
						bestRatio = ratio;
					}
				});
				if (best) page = best;
			},
			{ root, threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] }
		);
		for (const node of root.querySelectorAll<HTMLElement>('[data-pdf-page]'))
			observer.observe(node);

		return () => observer.disconnect();
	});

	$effect(() => {
		const next = effective;
		if (!lastScale) {
			lastScale = next;
			return;
		}
		if (Math.abs(next - lastScale) < 0.001) return;
		lastScale = next;
		const anchor = untrack(() => page);
		void tick().then(() => jump(anchor, 'instant'));
	});

	function jump(number: number, behavior: ScrollBehavior) {
		const node = viewport?.querySelector<HTMLElement>(`[data-pdf-page="${number}"]`);
		if (!node || !viewport) return;
		const top =
			node.getBoundingClientRect().top -
			viewport.getBoundingClientRect().top +
			viewport.scrollTop -
			GUTTER / 2;
		viewport.scrollTo({ top: Math.max(top, 0), behavior });
	}

	export function goTo(number: number) {
		jump(number, 'smooth');
	}
</script>

<div class="min-h-0 flex-1" bind:clientWidth={width} bind:clientHeight={height}>
	<ScrollArea class="h-full" bind:viewportRef={viewport}>
		<div class="flex flex-col items-center gap-6 py-10">
			{#each sizes as size, index (index)}
				{@const number = index + 1}
				<div
					data-pdf-page={number}
					use:visible={{
						root: viewport,
						margin: RENDER_MARGIN,
						onChange: (on) => (on ? live.add(number) : live.delete(number))
					}}
				>
					<PdfPage
						{doc}
						{number}
						{size}
						{scale}
						active={live.has(number)}
						class="ring-border/70 rounded-[2px] shadow-md ring-1"
					/>
				</div>
			{/each}
		</div>
	</ScrollArea>
</div>
