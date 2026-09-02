<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import * as Select from '$lib/components/ui/select';
	import X from '@lucide/svelte/icons/x';
	import Plus from '@lucide/svelte/icons/plus';
	import {
		MULTIPLIERS,
		type ScanContextRead,
		type ScanContextCreate
	} from '$lib/types/scan-context';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	$effect(() => {
		engineCatalogStore.fetch();
	});

	const rateTools = $derived(engineCatalogStore.catalog?.rate_tools ?? []);

	const MULTIPLIER_LABELS: { value: string; label: string }[] = MULTIPLIERS.map((m) => ({
		value: String(m),
		label: m === 1.0 ? '1× (default)' : `${m}×`
	}));

	const RATE_MIN = 1;
	const RATE_MAX = 10000;
	const RATE_ERR = `Enter a value between ${RATE_MIN} and ${RATE_MAX}`;

	function parseRate(raw: string): number | null {
		const t = raw.trim();
		if (t === '') return null;
		const n = Number(t);
		if (!Number.isInteger(n) || n < RATE_MIN || n > RATE_MAX) return null;
		return n;
	}

	let globalRaw = $state('');
	let globalError = $state(false);
	let globalCommitted: number | null = null;
	$effect(() => {
		const v = context.global_rate_limit_override;
		if (v !== globalCommitted) {
			globalCommitted = v ?? null;
			globalRaw = v == null ? '' : String(v);
			globalError = false;
		}
	});

	function setGlobalRate(raw: string) {
		globalRaw = raw;
		if (raw.trim() === '') {
			globalError = false;
			globalCommitted = null;
			onChange({ global_rate_limit_override: null });
			return;
		}
		const n = parseRate(raw);
		if (n === null) {
			globalError = true;
			return;
		}
		globalError = false;
		globalCommitted = n;
		onChange({ global_rate_limit_override: n });
	}

	function setMultiplier(key: 'thread_multiplier' | 'timeout_multiplier', v: string | undefined) {
		onChange({ [key]: v ? Number(v) : 1.0 } as Partial<CtxLike>);
	}

	let toolRows = $state<{ tool: string; rate: string }[]>([]);
	let toolsCommitted = '';
	$effect(() => {
		const incoming = JSON.stringify(context.per_tool_rate_overrides);
		if (incoming !== toolsCommitted) {
			toolsCommitted = incoming;
			toolRows = Object.entries(context.per_tool_rate_overrides).map(([tool, rate]) => ({
				tool,
				rate: String(rate)
			}));
		}
	});

	function rowError(rate: string): boolean {
		return rate.trim() !== '' && parseRate(rate) === null;
	}

	function commitTools() {
		const dict: Record<string, number> = {};
		for (const r of toolRows) {
			const n = parseRate(r.rate);
			if (r.tool && n !== null) dict[r.tool] = n;
		}
		toolsCommitted = JSON.stringify(dict);
		onChange({ per_tool_rate_overrides: dict });
	}

	function addToolRow() {
		const used = new Set(toolRows.map((r) => r.tool));
		const free = rateTools.find((t) => !used.has(t));
		if (!free) return;
		toolRows = [...toolRows, { tool: free, rate: '100' }];
		commitTools();
	}

	function updateToolRow(i: number, key: 'tool' | 'rate', v: string) {
		toolRows = toolRows.map((r, idx) => (idx === i ? { ...r, [key]: v } : r));
		commitTools();
	}

	function removeToolRow(i: number) {
		toolRows = toolRows.filter((_, idx) => idx !== i);
		commitTools();
	}

	let canAddTool = $derived(rateTools.length > 0 && toolRows.length < rateTools.length);

	function toolsFor(i: number): readonly string[] {
		const usedElsewhere = new Set(toolRows.filter((_, idx) => idx !== i).map((r) => r.tool));
		return rateTools.filter((t) => !usedElsewhere.has(t));
	}
</script>

<div class="space-y-5">
	<div class="space-y-1.5">
		<Label class="text-xs">Global rate limit override</Label>
		<Input
			type="number"
			min={RATE_MIN}
			max={RATE_MAX}
			value={globalRaw}
			placeholder="engine default · hard ceiling"
			class="h-9 max-w-xs {globalError ? 'border-destructive focus-visible:ring-destructive' : ''}"
			aria-invalid={globalError}
			oninput={(e) => setGlobalRate(e.currentTarget.value)}
		/>
		{#if globalError}
			<p class="text-xs text-destructive">{RATE_ERR}</p>
		{:else}
			<p class="text-xs text-muted-foreground">
				Requests/sec ceiling applied across the scan. Leave blank to use the engine's value.
			</p>
		{/if}
	</div>

	<div class="space-y-2">
		<Label class="text-xs">Per-tool rate overrides</Label>
		{#each toolRows as row, i (i)}
			{@const invalid = rowError(row.rate)}
			<div>
				<div class="flex items-center gap-2">
					<Select.Root
						type="single"
						value={row.tool}
						onValueChange={(v) => updateToolRow(i, 'tool', v ?? '')}
					>
						<Select.Trigger class="h-9 w-40 text-sm">
							{row.tool || 'Select tool'}
						</Select.Trigger>
						<Select.Content>
							{#each toolsFor(i) as tool (tool)}
								<Select.Item value={tool} label={tool}>{tool}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<Input
						type="number"
						min={RATE_MIN}
						max={RATE_MAX}
						value={row.rate}
						placeholder="rate"
						class="h-9 w-32 {invalid ? 'border-destructive focus-visible:ring-destructive' : ''}"
						aria-invalid={invalid}
						oninput={(e) => updateToolRow(i, 'rate', e.currentTarget.value)}
					/>
					<Button
						variant="ghost"
						size="icon"
						class="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
						onclick={() => removeToolRow(i)}
						aria-label="Remove override"
					>
						<X class="h-4 w-4" />
					</Button>
				</div>
				{#if invalid}
					<p class="mt-1 text-xs text-destructive">{RATE_ERR}</p>
				{/if}
			</div>
		{/each}
		{#if canAddTool}
			<Button
				variant="ghost"
				size="sm"
				class="h-8 gap-1.5 text-muted-foreground"
				onclick={addToolRow}
			>
				<Plus class="h-3.5 w-3.5" />
				Add tool override
			</Button>
		{/if}
	</div>

	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Label class="text-xs">Thread multiplier</Label>
			<Select.Root
				type="single"
				value={String(context.thread_multiplier)}
				onValueChange={(v) => setMultiplier('thread_multiplier', v)}
			>
				<Select.Trigger class="h-9 w-full text-sm">
					{MULTIPLIER_LABELS.find((m) => m.value === String(context.thread_multiplier))?.label ??
						'1×'}
				</Select.Trigger>
				<Select.Content>
					{#each MULTIPLIER_LABELS as opt (opt.value)}
						<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Timeout multiplier</Label>
			<Select.Root
				type="single"
				value={String(context.timeout_multiplier)}
				onValueChange={(v) => setMultiplier('timeout_multiplier', v)}
			>
				<Select.Trigger class="h-9 w-full text-sm">
					{MULTIPLIER_LABELS.find((m) => m.value === String(context.timeout_multiplier))?.label ??
						'1×'}
				</Select.Trigger>
				<Select.Content>
					{#each MULTIPLIER_LABELS as opt (opt.value)}
						<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
	</div>
</div>
