<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import * as Select from '$lib/components/ui/select';
	import { X, Plus } from 'lucide-svelte';
	import {
		VALID_RATE_TOOLS,
		MULTIPLIERS,
		type ScanContextRead,
		type ScanContextCreate
	} from '$lib/types/scan-context';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	const MULTIPLIER_LABELS: { value: string; label: string }[] = MULTIPLIERS.map((m) => ({
		value: String(m),
		label: m === 1.0 ? '1× (default)' : `${m}×`
	}));

	function setGlobalRate(raw: string) {
		if (raw.trim() === '') {
			onChange({ global_rate_limit_override: null });
			return;
		}
		const n = Math.trunc(Number(raw));
		onChange({ global_rate_limit_override: Number.isFinite(n) && n > 0 ? n : null });
	}

	function setMultiplier(key: 'thread_multiplier' | 'timeout_multiplier', v: string | undefined) {
		onChange({ [key]: v ? Number(v) : 1.0 } as Partial<CtxLike>);
	}

	// ── Per-tool overrides ──────────────────────────────────────────────────────
	let toolRows = $derived(
		Object.entries(context.per_tool_rate_overrides).map(([tool, rate]) => ({
			tool,
			rate: String(rate)
		}))
	);

	function commitTools(rows: { tool: string; rate: string }[]) {
		const dict: Record<string, number> = {};
		for (const r of rows) {
			const n = Number(r.rate);
			if (r.tool && Number.isFinite(n) && n > 0) dict[r.tool] = n;
		}
		onChange({ per_tool_rate_overrides: dict });
	}

	function addToolRow() {
		const used = new Set(toolRows.map((r) => r.tool));
		const free = VALID_RATE_TOOLS.find((t) => !used.has(t));
		if (!free) return;
		commitTools([...toolRows, { tool: free, rate: '100' }]);
	}

	function updateToolRow(i: number, key: 'tool' | 'rate', v: string) {
		const rows = toolRows.map((r) => ({ ...r }));
		rows[i][key] = v;
		commitTools(rows);
	}

	function removeToolRow(i: number) {
		commitTools(toolRows.filter((_, idx) => idx !== i));
	}

	let canAddTool = $derived(toolRows.length < VALID_RATE_TOOLS.length);

	// Tools available to a given row: those not used by *other* rows (a row keeps
	// its own tool selectable). Prevents two rows collapsing onto the same tool.
	function toolsFor(i: number): readonly string[] {
		const usedElsewhere = new Set(toolRows.filter((_, idx) => idx !== i).map((r) => r.tool));
		return VALID_RATE_TOOLS.filter((t) => !usedElsewhere.has(t));
	}
</script>

<div class="space-y-5">
	<!-- Global rate -->
	<div class="space-y-1.5">
		<Label class="text-xs">Global rate limit override</Label>
		<Input
			type="number"
			min="1"
			max="10000"
			value={context.global_rate_limit_override ?? ''}
			placeholder="engine default · hard ceiling"
			class="h-9 max-w-xs"
			oninput={(e) => setGlobalRate(e.currentTarget.value)}
		/>
		<p class="text-xs text-muted-foreground">
			Requests/sec ceiling applied across the scan. Leave blank to use the engine's value.
		</p>
	</div>

	<!-- Per-tool overrides -->
	<div class="space-y-2">
		<Label class="text-xs">Per-tool rate overrides</Label>
		{#each toolRows as row, i (i)}
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
					min="1"
					max="10000"
					value={row.rate}
					placeholder="rate"
					class="h-9 w-32"
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
		{/each}
		{#if canAddTool}
			<Button variant="ghost" size="sm" class="h-8 gap-1.5 text-muted-foreground" onclick={addToolRow}>
				<Plus class="h-3.5 w-3.5" />
				Add tool override
			</Button>
		{/if}
	</div>

	<!-- Multipliers -->
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Label class="text-xs">Thread multiplier</Label>
			<Select.Root
				type="single"
				value={String(context.thread_multiplier)}
				onValueChange={(v) => setMultiplier('thread_multiplier', v)}
			>
				<Select.Trigger class="h-9 w-full text-sm">
					{MULTIPLIER_LABELS.find((m) => m.value === String(context.thread_multiplier))?.label ?? '1×'}
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
					{MULTIPLIER_LABELS.find((m) => m.value === String(context.timeout_multiplier))?.label ?? '1×'}
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
