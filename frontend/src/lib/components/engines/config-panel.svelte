<script lang="ts">
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';
	import { Textarea } from '$lib/components/ui/textarea';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import * as Select from '$lib/components/ui/select';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import X from '@lucide/svelte/icons/x';
	import Key from '@lucide/svelte/icons/key';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import type { Snippet } from 'svelte';
	import type { DiscoveryConfig, ExpansionConfig, DepthConfig } from '$lib/types/engine';
	import { PHASE_COLORS } from '$lib/types/engine';
	import { CAPABILITIES } from '$lib/types/capabilities';
	import { parseCsv, parseLines } from '$lib/utilities/parse';
	import { CAPABILITY_FIELDS, type FieldSpec } from './capability-fields';

	interface Props {
		capabilityId: string | null;
		phase: 'discovery' | 'expansion' | 'depth' | null;
		config: DiscoveryConfig | ExpansionConfig | DepthConfig | null;
		onChange?: (updates: Record<string, unknown>) => void;
		onClose?: () => void;
	}

	let { capabilityId, phase, config, onChange, onClose }: Props = $props();

	let phaseColor = $derived(phase ? PHASE_COLORS[phase] : null);
	let capability = $derived(capabilityId ? CAPABILITIES.find((c) => c.id === capabilityId) : null);
	let capLabel = $derived(capability?.label ?? capabilityId ?? '');
	let sections = $derived(capabilityId ? (CAPABILITY_FIELDS[capabilityId] ?? []) : []);

	let localConfig = $state<Record<string, unknown>>({});

	$effect(() => {
		if (config) {
			localConfig = JSON.parse(JSON.stringify(config));
		}
	});

	function get<T>(path: string, fallback: T): T {
		const parts = path.split('.');
		let cur: unknown = localConfig;
		for (const p of parts) {
			if (cur == null || typeof cur !== 'object') return fallback;
			cur = (cur as Record<string, unknown>)[p];
		}
		return cur === undefined ? fallback : (cur as T);
	}

	function set(path: string, value: unknown) {
		const parts = path.split('.');
		let cur = localConfig as Record<string, unknown>;
		for (let i = 0; i < parts.length - 1; i++) {
			if (cur[parts[i]] == null || typeof cur[parts[i]] !== 'object') {
				cur[parts[i]] = {};
			}
			cur = cur[parts[i]] as Record<string, unknown>;
		}
		cur[parts[parts.length - 1]] = value;
		onChange?.(localConfig);
	}

	function toggleArray(path: string, val: string) {
		const arr = get<string[]>(path, []);
		const next = arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
		set(path, next);
	}

	function toggleIntArray(path: string, val: number) {
		const arr = get<number[]>(path, []);
		const next = arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
		set(path, next);
	}

	function hasInArray(path: string, val: string): boolean {
		return get<string[]>(path, []).includes(val);
	}

	function hasInIntArray(path: string, val: number): boolean {
		return get<number[]>(path, []).includes(val);
	}

	let openSections = $state<Record<string, boolean>>({});

	function sectionOpen(key: string): boolean {
		return openSections[key] !== false;
	}
</script>

{#if capabilityId}
	<div class="config-panel">
		<div class="panel-header">
			<div class="header-content">
				<div class="header-text">
					<span
						class="phase-dot"
						style="background: {phaseColor?.accent ?? 'var(--muted-foreground)'};"
					></span>
					<span class="cap-title">{capLabel}</span>
				</div>
				<Button variant="ghost" size="icon-sm" onclick={() => onClose?.()}>
					<X size={16} />
				</Button>
			</div>
		</div>

		<ScrollArea class="panel-body">
			<div class="body-inner">
				{#each sections as sect (sect.key)}
					{#snippet body()}
						{#each sect.fields as field, i (i)}
							{@render renderField(field)}
						{/each}
					{/snippet}
					{@render section(sect.key, sect.title, body)}
				{/each}
			</div>
		</ScrollArea>

		<div class="panel-footer">
			<Button variant="outline" class="w-full" onclick={() => onClose?.()}>Close</Button>
		</div>
	</div>
{/if}

{#snippet section(key: string, title: string, body: Snippet)}
	<Collapsible.Root bind:open={() => sectionOpen(key), (v) => (openSections[key] = v)}>
		<Collapsible.Trigger class="section-trigger">
			<span class="section-title">{title}</span>
			<ChevronDown size={14} class="section-chevron" data-open={sectionOpen(key)} />
		</Collapsible.Trigger>
		<Collapsible.Content class="sect-body">
			{@render body()}
		</Collapsible.Content>
	</Collapsible.Root>
{/snippet}

{#snippet toggleRow(label: string, path: string, fallback: boolean)}
	<div class="toggle-row">
		<Label class="field-label" for="sw-{path}">{label}</Label>
		<Switch id="sw-{path}" checked={get(path, fallback)} onCheckedChange={(v) => set(path, v)} />
	</div>
{/snippet}

{#snippet toggleKey(label: string, path: string, fallback: boolean, keyName: string)}
	<div class="toggle-row">
		<Label class="field-label" for="sw-{path}">
			{label}
			<Badge variant="outline" class="key-badge"><Key size={9} />{keyName}</Badge>
		</Label>
		<Switch id="sw-{path}" checked={get(path, fallback)} onCheckedChange={(v) => set(path, v)} />
	</div>
{/snippet}

{#snippet numberRow(label: string, path: string, fallback: number)}
	<div class="toggle-row">
		<Label class="field-label" for="num-{path}">{label}</Label>
		<Input
			id="num-{path}"
			type="number"
			value={get(path, fallback)}
			oninput={(e) => set(path, Number(e.currentTarget.value))}
			class="w-24 text-sm"
		/>
	</div>
{/snippet}

{#snippet radioGroup(path: string, fallback: string, options: { value: string; label: string }[])}
	<RadioGroup.Root value={get(path, fallback)} onValueChange={(v) => set(path, v)} class="gap-2">
		{#each options as opt (opt.value)}
			<div class="radio-row">
				<RadioGroup.Item value={opt.value} id="{path}-{opt.value}" />
				<Label for="{path}-{opt.value}" class="field-label">{opt.label}</Label>
			</div>
		{/each}
	</RadioGroup.Root>
{/snippet}

{#snippet boolRadioGroup(
	path: string,
	fallback: boolean,
	options: { value: boolean; label: string }[]
)}
	<RadioGroup.Root
		value={String(get(path, fallback))}
		onValueChange={(v) => set(path, v === 'true')}
		class="gap-2"
	>
		{#each options as opt (String(opt.value))}
			<div class="radio-row">
				<RadioGroup.Item value={String(opt.value)} id="{path}-{String(opt.value)}" />
				<Label for="{path}-{String(opt.value)}" class="field-label">{opt.label}</Label>
			</div>
		{/each}
	</RadioGroup.Root>
{/snippet}

{#snippet checkGroup(path: string, options: { value: string; label: string }[])}
	<div class="check-group">
		{#each options as opt (opt.value)}
			<div class="check-row">
				<Checkbox
					id="{path}-{opt.value}"
					checked={hasInArray(path, opt.value)}
					onCheckedChange={() => toggleArray(path, opt.value)}
				/>
				<Label for="{path}-{opt.value}" class="check-label">{opt.label}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet checkChips(path: string, values: string[], upper = false)}
	<div class="chip-wrap">
		{#each values as v (v)}
			<div class="chip-row">
				<Checkbox
					id="{path}-{v}"
					checked={hasInArray(path, v)}
					onCheckedChange={() => toggleArray(path, v)}
				/>
				<Label for="{path}-{v}" class="chip-label">{upper ? v.toUpperCase() : v}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet checkChipsInt(path: string, values: number[])}
	<div class="chip-wrap">
		{#each values as v (v)}
			<div class="chip-row">
				<Checkbox
					id="{path}-{v}"
					checked={hasInIntArray(path, v)}
					onCheckedChange={() => toggleIntArray(path, v)}
				/>
				<Label for="{path}-{v}" class="chip-label">{v}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet selectRow(
	label: string,
	path: string,
	fallback: string,
	options: { value: string; label: string }[]
)}
	<div class="field-col">
		<Label class="field-sub">{label}</Label>
		<Select.Root
			type="single"
			value={get(path, fallback)}
			onValueChange={(v) => set(path, v ?? '')}
		>
			<Select.Trigger class="w-full text-sm">
				{options.find((o) => o.value === get(path, fallback))?.label ?? 'Select…'}
			</Select.Trigger>
			<Select.Content>
				{#each options as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
{/snippet}

{#snippet hint(text: string)}
	<p class="hint">{text}</p>
{/snippet}

{#snippet textRow(
	label: string,
	path: string,
	fallback: string,
	placeholder: string,
	mono: boolean
)}
	<div class="field-col">
		<Label for="txt-{path}" class="field-sub">{label}</Label>
		<Input
			id="txt-{path}"
			{placeholder}
			value={get(path, fallback)}
			oninput={(e) => set(path, e.currentTarget.value)}
			class={mono ? 'text-sm font-mono' : 'text-sm'}
		/>
	</div>
{/snippet}

{#snippet textCsvRow(label: string, path: string, placeholder: string)}
	<div class="field-col">
		<Label for="txt-{path}" class="field-sub">{label}</Label>
		<Input
			id="txt-{path}"
			{placeholder}
			value={get<string[]>(path, []).join(',')}
			oninput={(e) => set(path, parseCsv(e.currentTarget.value))}
			class="text-sm font-mono"
		/>
	</div>
{/snippet}

{#snippet csvArea(path: string)}
	<Textarea
		class="text-xs font-mono"
		value={get<string[]>(path, []).join(', ')}
		oninput={(e) => set(path, parseCsv(e.currentTarget.value))}
	/>
{/snippet}

{#snippet linesArea(path: string)}
	<Textarea
		class="text-xs font-mono"
		value={get<string[]>(path, []).join('\n')}
		oninput={(e) => set(path, parseLines(e.currentTarget.value))}
	/>
{/snippet}

{#snippet renderField(field: FieldSpec)}
	{#if field.kind === 'toggle'}
		{@render toggleRow(field.label, field.path, field.fallback)}
	{:else if field.kind === 'togglekey'}
		{@render toggleKey(field.label, field.path, field.fallback, field.keyName)}
	{:else if field.kind === 'number'}
		{@render numberRow(field.label, field.path, field.fallback)}
	{:else if field.kind === 'radio'}
		{@render radioGroup(field.path, field.fallback, field.options)}
	{:else if field.kind === 'boolradio'}
		{@render boolRadioGroup(field.path, field.fallback, field.options)}
	{:else if field.kind === 'checkgroup'}
		{@render checkGroup(field.path, field.options)}
	{:else if field.kind === 'checkchips'}
		{@render checkChips(field.path, field.values, field.upper ?? false)}
	{:else if field.kind === 'checkchipsint'}
		{@render checkChipsInt(field.path, field.values)}
	{:else if field.kind === 'select'}
		{@render selectRow(field.label, field.path, field.fallback, field.options)}
	{:else if field.kind === 'hint'}
		{@render hint(field.text)}
	{:else if field.kind === 'text'}
		{@render textRow(
			field.label,
			field.path,
			field.fallback,
			field.placeholder ?? '',
			field.mono ?? true
		)}
	{:else if field.kind === 'textcsv'}
		{@render textCsvRow(field.label, field.path, field.placeholder ?? '')}
	{:else if field.kind === 'csv'}
		{@render csvArea(field.path)}
	{:else if field.kind === 'lines'}
		{@render linesArea(field.path)}
	{/if}
{/snippet}

<style>
	:global(.config-panel) {
		width: 384px;
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--card);
		border-left: 1px solid var(--border);
		overflow: hidden;
	}

	:global(.panel-header) {
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
	}

	:global(.header-content) {
		padding: 14px 18px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}

	:global(.header-text) {
		display: flex;
		align-items: center;
		gap: 9px;
		min-width: 0;
	}

	:global(.phase-dot) {
		width: 8px;
		height: 8px;
		border-radius: 999px;
		flex-shrink: 0;
	}

	:global(.cap-title) {
		font-size: 15px;
		font-weight: 600;
		color: var(--foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	:global(.panel-body) {
		flex: 1;
		min-height: 0;
	}

	:global(.body-inner) {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	:global(.sect-body) {
		padding: 12px 4px 4px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	:global(.field-col) {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	:global(.field-sub) {
		font-size: 12px;
		color: var(--muted-foreground);
	}

	:global(.check-group) {
		display: flex;
		flex-direction: column;
		gap: 9px;
	}

	:global(.chip-wrap) {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 16px;
	}

	:global(.hint) {
		font-size: 12px;
		color: var(--muted-foreground);
		line-height: 1.5;
	}

	:global(.panel-footer) {
		padding: 10px 16px;
		border-top: 1px solid var(--border);
		flex-shrink: 0;
		display: flex;
		gap: 8px;
	}

	:global(.section-trigger) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 8px 12px;
		background: var(--muted);
		border-radius: 8px;
		border: 1px solid var(--border);
		cursor: pointer;
		user-select: none;
		transition: background 0.12s;
	}

	:global(.section-trigger:hover) {
		background: var(--accent);
	}

	:global(.section-title) {
		font-size: 10px;
		font-weight: 700;
		color: var(--foreground);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	:global(.section-chevron) {
		color: var(--muted-foreground);
		transition: transform 0.15s ease;
	}

	:global(.section-chevron[data-open='false']) {
		transform: rotate(-90deg);
	}

	:global(.toggle-row) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	:global(.field-label) {
		font-size: 12px;
		color: var(--foreground);
		flex: 1;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
	}

	:global(.radio-row),
	:global(.check-row) {
		display: flex;
		align-items: center;
		gap: 9px;
	}

	:global(.check-label) {
		flex: 1;
		font-size: 12px;
		color: var(--foreground);
		cursor: pointer;
	}

	:global(.chip-row) {
		display: inline-flex;
		align-items: center;
		gap: 7px;
	}

	:global(.chip-label) {
		font-size: 12px;
		color: var(--foreground);
		cursor: pointer;
		font-family: var(--font-mono);
	}

	:global(.key-badge) {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-size: 9px;
		font-weight: 600;
		padding: 1px 5px;
	}
</style>
