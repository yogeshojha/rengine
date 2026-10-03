<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Kbd from '$lib/components/ui/kbd';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { ROUTES } from '$lib/config/routes';
	import { VISUAL_FIELD_LABELS } from '$lib/config/whats-new';
	import { screenshotUrl } from '$lib/utilities/media';
	import { screenshotDiff, type ScreenshotDiff } from '$lib/utilities/screenshot-diff';
	import { visualChange } from '$lib/utilities/whats-new';
	import { keyTaken } from '$lib/utilities/layers';
	import { SvelteMap } from 'svelte/reactivity';
	import type { VisualPair } from '$lib/types/whats-new';

	interface Props {
		pairs: VisualPair[];
		index: number;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onStep: (dir: -1 | 1) => void;
		onOpenHost: (pair: VisualPair) => void;
	}

	let { pairs, index, open, onOpenChange, onStep, onOpenHost }: Props = $props();

	const MODES = [
		{ key: 'wipe', label: 'Wipe' },
		{ key: 'side', label: 'Side by side' },
		{ key: 'diff', label: 'Diff' }
	] as const;
	type Mode = (typeof MODES)[number]['key'];

	let mode = $state<Mode>('wipe');
	let wipe = $state(50);
	let holdBefore = $state(false);
	let dragging = $state(false);
	let stage = $state<HTMLDivElement | null>(null);
	const diffs = new SvelteMap<string, ScreenshotDiff | 'loading' | 'failed'>();

	let pair = $derived(pairs[index] ?? null);
	let beforeUrl = $derived(pair ? screenshotUrl(pair.before_path) : null);
	let afterUrl = $derived(pair ? screenshotUrl(pair.after_path) : null);
	let diff = $derived(pair ? (diffs.get(pair.id) ?? null) : null);
	let position = $derived(holdBefore ? 100 : wipe);

	$effect(() => {
		if (!open || mode !== 'diff' || !pair || !beforeUrl || !afterUrl || diffs.has(pair.id)) return;
		const id = pair.id;
		diffs.set(id, 'loading');
		screenshotDiff(beforeUrl, afterUrl)
			.then((d) => diffs.set(id, d))
			.catch(() => diffs.set(id, 'failed'));
	});

	function setWipe(e: PointerEvent) {
		if (!stage) return;
		const rect = stage.getBoundingClientRect();
		wipe = Math.round(Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100)));
	}
	function down(e: PointerEvent) {
		if (mode !== 'wipe' || e.button !== 0) return;
		dragging = true;
		setWipe(e);
	}
	function move(e: PointerEvent) {
		if (dragging) setWipe(e);
	}
	function up() {
		dragging = false;
	}

	function onKey(e: KeyboardEvent) {
		if (!open || keyTaken(e.target)) return;
		const el = e.target instanceof Element ? e.target : null;
		const arrow = e.key === 'ArrowRight' || e.key === 'ArrowLeft';
		if (arrow && el?.closest('[role=radio]')) return;
		if (e.key === ' ' && el?.closest('button, [role=radio]')) return;
		if (e.key === 'ArrowRight' || e.key === 'j') {
			e.preventDefault();
			onStep(1);
		} else if (e.key === 'ArrowLeft' || e.key === 'k') {
			e.preventDefault();
			onStep(-1);
		} else if (e.key === ' ' && !e.repeat) {
			e.preventDefault();
			holdBefore = true;
		} else if (e.key === '1' || e.key === '2' || e.key === '3') {
			mode = MODES[Number(e.key) - 1].key;
		}
	}
	function onKeyUp(e: KeyboardEvent) {
		if (e.key === ' ') holdBefore = false;
	}
</script>

<svelte:window onkeydown={onKey} onkeyup={onKeyUp} onpointerup={up} onpointermove={move} />

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-7xl">
		{#if pair}
			<Dialog.Header class="gap-2 border-b px-6 py-4 pr-12">
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
					<Dialog.Title class="font-mono break-all">{pair.host}</Dialog.Title>
					<a
						href={ROUTES.target(pair.target_id)}
						class="text-xs text-muted-foreground hover:text-foreground">{pair.target_value}</a
					>
					<span class="text-xs text-muted-foreground tabular-nums">Distance {pair.distance}</span>
					{#if pair.silent}
						<Badge variant="warning">Silent redeploy</Badge>
					{:else}
						{#each pair.moved as field (field)}
							<Badge variant="secondary" class="font-normal">
								{VISUAL_FIELD_LABELS[field] ?? field} · {visualChange(pair, field)}
							</Badge>
						{/each}
					{/if}
					<span class="ml-auto flex items-center gap-2">
						<ToggleGroup.Root
							type="single"
							value={mode}
							onValueChange={(v) => v && (mode = v as Mode)}
							variant="outline"
							size="sm"
							aria-label="View"
						>
							{#each MODES as m, i (m.key)}
								<ToggleGroup.Item value={m.key} class="h-7 gap-1.5 px-2 text-xs font-normal">
									{m.label}
									<Kbd.Root class="h-4 min-w-4 text-2xs">{i + 1}</Kbd.Root>
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</span>
				</div>
				<Dialog.Description class="sr-only">Before and after screenshots.</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(90vh-9.5rem)]"
			>
				{#if mode === 'side'}
					<div class="grid grid-cols-2 gap-px bg-border">
						<figure class="relative bg-muted">
							<img src={beforeUrl} alt="{pair.host} before" class="block w-full" />
							<figcaption class="absolute top-2 left-2 rounded-sm bg-background/90 px-1.5 text-2xs">
								Before
							</figcaption>
						</figure>
						<figure class="relative bg-muted">
							<img src={afterUrl} alt="{pair.host} after" class="block w-full" />
							<figcaption class="absolute top-2 left-2 rounded-sm bg-background/90 px-1.5 text-2xs">
								After
							</figcaption>
						</figure>
					</div>
				{:else if mode === 'diff'}
					<div class="relative bg-muted">
						<img src={afterUrl} alt="{pair.host} after" class="block w-full" />
						{#if diff === 'loading' || diff === null}
							<div class="absolute inset-0 flex items-center justify-center bg-background/60">
								<Spinner class="size-5 text-muted-foreground" />
							</div>
						{:else if diff === 'failed'}
							<div class="absolute top-2 left-2 rounded-sm bg-background/90 px-1.5 text-2xs">
								Diff not computed
							</div>
						{:else}
							<svg
								class="pointer-events-none absolute inset-0 h-full w-full"
								viewBox="0 0 {diff.width} {diff.height}"
								preserveAspectRatio="none"
								aria-hidden="true"
							>
								{#each diff.boxes as box, i (i)}
									<rect
										x={box.x}
										y={box.y}
										width={box.w}
										height={box.h}
										fill="var(--destructive)"
										fill-opacity="0.35"
									/>
								{/each}
							</svg>
							<div
								class="absolute top-2 left-2 rounded-sm bg-background/90 px-1.5 text-2xs tabular-nums"
							>
								{Math.round(diff.ratio * 100)}% of the page changed
							</div>
						{/if}
					</div>
				{:else}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						bind:this={stage}
						class="relative cursor-col-resize bg-muted select-none"
						onpointerdown={down}
					>
						<img src={afterUrl} alt="{pair.host} after" class="block w-full" draggable="false" />
						<img
							src={beforeUrl}
							alt="{pair.host} before"
							draggable="false"
							class="absolute inset-0 block w-full"
							style="clip-path: inset(0 {100 - position}% 0 0)"
						/>
						<div
							class="pointer-events-none absolute inset-y-0 w-px bg-primary"
							style="left: {position}%"
						>
							<span
								class="absolute top-1/2 left-1/2 flex size-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-primary bg-background text-2xs"
							>
								⇔
							</span>
						</div>
						<span class="absolute top-2 left-2 rounded-sm bg-background/90 px-1.5 text-2xs"
							>Before</span
						>
						<span class="absolute top-2 right-2 rounded-sm bg-background/90 px-1.5 text-2xs"
							>After</span
						>
						<label class="sr-only">
							Wipe position
							<input type="range" min="0" max="100" bind:value={wipe} />
						</label>
					</div>
				{/if}
			</ScrollArea>

			<div
				class="flex flex-wrap items-center gap-x-4 gap-y-2 border-t px-6 py-4 text-xs text-muted-foreground"
			>
				<span class="flex items-center gap-1">
					<Button
						variant="ghost"
						size="icon-sm"
						aria-label="Previous"
						disabled={index <= 0}
						onclick={() => onStep(-1)}
					>
						<ChevronLeft class="size-4" />
					</Button>
					<span class="tabular-nums">{index + 1} of {pairs.length}</span>
					<Button
						variant="ghost"
						size="icon-sm"
						aria-label="Next"
						disabled={index >= pairs.length - 1}
						onclick={() => onStep(1)}
					>
						<ChevronRight class="size-4" />
					</Button>
				</span>
				<span class="flex items-center gap-1.5"><Kbd.Root>Space</Kbd.Root> hold for before</span>
				<span class="flex items-center gap-1.5"><Kbd.Root>← →</Kbd.Root> step</span>
				<span class="ml-auto flex items-center gap-2">
					<Button variant="outline" size="sm" onclick={() => onOpenHost(pair)}>
						Open web asset
					</Button>
					<Button
						variant="outline"
						size="sm"
						href={ROUTES.compare(pair.scan_id, pair.previous_scan_id)}
					>
						Compare runs
					</Button>
				</span>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
