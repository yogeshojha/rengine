<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Gauge from '@lucide/svelte/icons/gauge';
	import {
		INTENSITY_LABELS,
		hasCustomTransport,
		type Intensity,
		type TransportOverrides
	} from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		intensity: Intensity;
		overrides: TransportOverrides;
		rateTools: string[];
		presetRates: Record<string, number>;
		presetThreads: Record<string, number>;
		onOpenChange: (open: boolean) => void;
		onChange: (overrides: TransportOverrides) => void;
	}

	let {
		open,
		intensity,
		overrides,
		rateTools,
		presetRates,
		presetThreads,
		onOpenChange,
		onChange
	}: Props = $props();

	const custom = $derived(hasCustomTransport(overrides));

	function edit(tool: string, field: 'rate' | 'threads', raw: string) {
		const next: TransportOverrides = structuredClone($state.snapshot(overrides)) ?? {};
		const value = raw.trim() === '' ? null : Math.max(1, Math.round(Number(raw)));
		const entry = { ...(next[tool] ?? {}) };
		if (value === null || Number.isNaN(value)) delete entry[field];
		else entry[field] = value;
		if (entry.rate == null && entry.threads == null) delete next[tool];
		else next[tool] = entry;
		onChange(next);
	}

	function reset() {
		onChange({});
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-[calc(100%-2rem)] flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title class="flex items-center gap-2 text-base">
				<Gauge size={16} class="text-muted-foreground" />
				Scan rates
			</Sheet.Title>
			<Sheet.Description>
				Requests a second and concurrency per tool. Empty uses the {INTENSITY_LABELS[
					intensity
				]?.toLowerCase() ?? intensity} preset.
			</Sheet.Description>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="px-5 py-4">
				<div
					class="grid grid-cols-[1fr_5.5rem_5.5rem] items-center gap-x-3 gap-y-1 pb-2 text-2xs font-semibold uppercase tracking-wide text-muted-foreground"
				>
					<span>Tool</span>
					<span class="text-right">Req/sec</span>
					<span class="text-right">Threads</span>
				</div>
				<div class="divide-y">
					{#each rateTools as tool (tool)}
						{@const o = overrides[tool] ?? {}}
						<div class="grid grid-cols-[1fr_5.5rem_5.5rem] items-center gap-x-3 py-2">
							<Label for="rate-{tool}" class="font-mono text-xs">{tool}</Label>
							<Input
								id="rate-{tool}"
								type="number"
								min="1"
								inputmode="numeric"
								value={o.rate ?? ''}
								placeholder={String(presetRates[tool] ?? '')}
								oninput={(e) => edit(tool, 'rate', e.currentTarget.value)}
								class="h-8 text-right text-xs tabular-nums {o.rate != null
									? 'border-primary/50'
									: ''}"
								autocomplete="off"
							/>
							<Input
								id="threads-{tool}"
								type="number"
								min="1"
								inputmode="numeric"
								value={o.threads ?? ''}
								placeholder={String(presetThreads[tool] ?? '')}
								oninput={(e) => edit(tool, 'threads', e.currentTarget.value)}
								class="h-8 text-right text-xs tabular-nums {o.threads != null
									? 'border-primary/50'
									: ''}"
								autocomplete="off"
							/>
						</div>
					{/each}
				</div>
			</div>
		</ScrollArea>

		<div class="flex items-center justify-between border-t px-5 py-3">
			<span class="text-xs text-muted-foreground">
				{custom ? 'Custom rates set' : `${INTENSITY_LABELS[intensity] ?? intensity} preset`}
			</span>
			<Button variant="ghost" size="sm" class="h-8 text-xs" disabled={!custom} onclick={reset}>
				Reset to preset
			</Button>
		</div>
	</Sheet.Content>
</Sheet.Root>
