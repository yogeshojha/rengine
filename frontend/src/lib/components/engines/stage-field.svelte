<script lang="ts">
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Select from '$lib/components/ui/select';
	import Check from '@lucide/svelte/icons/check';
	import type { StageField } from '$lib/types/scan-engine';
	import { SCALE_HELP } from '$lib/types/scan-engine';
	import { parseCsv } from '$lib/utilities/parse';

	interface Props {
		field: StageField;
		value: unknown;
		stageName: string;
		onChange: (value: unknown) => void;
	}

	let { field, value, stageName, onChange }: Props = $props();

	const id = $derived(`${stageName}-${field.name}`);
	const boolValue = $derived(value === undefined ? Boolean(field.default) : Boolean(value));
	const listValue = $derived<string[]>(
		Array.isArray(value) ? (value as string[]) : ((field.default as string[]) ?? [])
	);

	function toggleListItem(option: string) {
		const next = listValue.includes(option)
			? listValue.filter((v) => v !== option)
			: [...listValue, option];
		onChange(next);
	}

	function commitNumber(raw: string) {
		const parsed = Number(raw);
		if (raw === '' || Number.isNaN(parsed)) return;
		let next = parsed;
		if (field.minimum !== null) next = Math.max(field.minimum, next);
		if (field.maximum !== null) next = Math.min(field.maximum, next);
		onChange(next);
	}
</script>

<div class="field" class:inline={field.type === 'boolean'}>
	<div class="label-col">
		<Label for={id} class="text-sm font-normal">{field.title}</Label>
		{#if field.description}
			<p class="help">{field.description}</p>
		{/if}
		{#if field.scale}
			<p class="help scale-help">{SCALE_HELP[field.scale]}</p>
		{/if}
	</div>

	<div class="control">
		{#if field.type === 'boolean'}
			<Switch {id} checked={boolValue} onCheckedChange={(v) => onChange(v)} />
		{:else if field.type === 'array' && field.options}
			<div class="chips">
				{#each field.options as option (option)}
					{@const on = listValue.includes(option)}
					<button
						type="button"
						class="chip"
						class:on
						aria-pressed={on}
						onclick={() => toggleListItem(option)}
					>
						{#if on}<Check size={11} />{/if}
						{option}
					</button>
				{/each}
			</div>
		{:else if field.type === 'array'}
			<Input
				{id}
				class="h-8 w-[260px] text-sm"
				value={listValue.join(', ')}
				placeholder="comma separated"
				onchange={(e) => onChange(parseCsv(e.currentTarget.value))}
				autocomplete="off"
				spellcheck={false}
			/>
		{:else if field.options}
			<Select.Root
				type="single"
				value={String(value ?? field.default ?? '')}
				onValueChange={(v) => v && onChange(v)}
			>
				<Select.Trigger {id} class="h-8 w-[200px] text-sm">
					{String(value ?? field.default ?? 'Select…')}
				</Select.Trigger>
				<Select.Content>
					{#each field.options as option (option)}
						<Select.Item value={option} label={option}>{option}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{:else if field.type === 'integer' || field.type === 'number'}
			<div class="num">
				<Input
					{id}
					type="number"
					class="h-8 w-24 text-sm"
					min={field.minimum ?? undefined}
					max={field.maximum ?? undefined}
					value={String(value ?? field.default ?? '')}
					onchange={(e) => commitNumber(e.currentTarget.value)}
				/>
				{#if field.minimum !== null && field.maximum !== null}
					<Badge variant="outline" class="range">{field.minimum}–{field.maximum}</Badge>
				{/if}
			</div>
		{:else}
			<Input
				{id}
				class="h-8 w-[260px] text-sm"
				value={String(value ?? field.default ?? '')}
				oninput={(e) => onChange(e.currentTarget.value)}
				autocomplete="off"
				spellcheck={false}
			/>
		{/if}
	</div>
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px 0;
	}
	.field.inline {
		flex-direction: row;
		align-items: flex-start;
		justify-content: space-between;
		gap: 24px;
	}
	.label-col {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.help {
		font-size: 11px;
		line-height: 1.45;
		color: var(--muted-foreground);
	}
	.scale-help {
		opacity: 0.75;
	}
	.control {
		flex-shrink: 0;
	}
	.num {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.num :global(.range) {
		font-size: 10px;
		font-weight: 400;
		color: var(--muted-foreground);
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 24px;
		padding: 0 9px;
		border-radius: 6px;
		border: 1px solid var(--border);
		background: var(--background);
		color: var(--muted-foreground);
		font-size: 11px;
		font-family: var(--font-mono, ui-monospace, monospace);
		cursor: pointer;
		transition:
			background 0.12s ease,
			color 0.12s ease,
			border-color 0.12s ease;
	}
	.chip:hover {
		border-color: var(--ring);
		color: var(--foreground);
	}
	.chip.on {
		background: var(--foreground);
		border-color: var(--foreground);
		color: var(--background);
	}
</style>
