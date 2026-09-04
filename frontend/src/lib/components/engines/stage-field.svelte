<script lang="ts">
	import * as Field from '$lib/components/ui/field';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import type { StageField } from '$lib/types/scan-engine';
	import { SCALE_HELP } from '$lib/types/scan-engine';
	import { parseCsv } from '$lib/utilities/parse';
	import CustomTemplatesField from './custom-templates-field.svelte';

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
	const modified = $derived(
		value !== undefined && JSON.stringify(value) !== JSON.stringify(field.default)
	);
	const defaultLabel = $derived(
		Array.isArray(field.default) ? field.default.join(', ') || '(none)' : String(field.default)
	);

	const optionLabel = (option: string) => field.option_labels?.[option] ?? option ?? 'Select…';

	function commitNumber(raw: string) {
		const parsed = Number(raw);
		if (raw === '' || Number.isNaN(parsed)) return;
		let next = parsed;
		if (field.minimum !== null) next = Math.max(field.minimum, next);
		if (field.maximum !== null) next = Math.min(field.maximum, next);
		onChange(next);
	}
</script>

<Field.Field orientation="horizontal" class="gap-6 py-2.5">
	<Field.Content class="gap-0.5">
		<span class="flex items-center gap-1.5">
			<Field.Label for={id} class="text-[13px] font-normal">{field.title}</Field.Label>
			{#if modified}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="h-5 w-5 text-primary hover:text-primary"
								onclick={() => onChange(field.default)}
							>
								<RotateCcw size={11} />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="text-xs">Reset to default ({defaultLabel})</Tooltip.Content>
				</Tooltip.Root>
			{/if}
		</span>
		{#if field.description}
			<Field.Description class="text-[11px] leading-snug">{field.description}</Field.Description>
		{/if}
		{#if field.scale}
			<Field.Description class="text-[11px] leading-snug opacity-75">
				{SCALE_HELP[field.scale]}
			</Field.Description>
		{/if}
	</Field.Content>

	<div class="shrink-0">
		{#if field.type === 'boolean'}
			<Switch {id} checked={boolValue} onCheckedChange={(v) => onChange(v)} />
		{:else if field.widget === 'custom_templates'}
			<CustomTemplatesField {id} value={listValue} onChange={(v) => onChange(v)} />
		{:else if field.type === 'array' && field.options}
			<ToggleGroup.Root
				type="multiple"
				variant="outline"
				size="sm"
				spacing={1}
				value={listValue}
				onValueChange={(v) => onChange(v)}
				class="max-w-[320px] flex-wrap justify-end"
				aria-label={field.title}
			>
				{#each field.options as option (option)}
					<ToggleGroup.Item
						value={option}
						class="h-6 px-2 text-[11px] font-normal aria-pressed:bg-foreground aria-pressed:text-background data-[state=on]:bg-foreground data-[state=on]:text-background"
					>
						{optionLabel(option)}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
		{:else if field.type === 'array'}
			<Input
				{id}
				class="h-8 w-[240px] text-sm"
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
				<Select.Trigger {id} class="h-8 w-[180px] text-sm">
					{optionLabel(String(value ?? field.default ?? ''))}
				</Select.Trigger>
				<Select.Content>
					{#each field.options as option (option)}
						<Select.Item value={option} label={optionLabel(option)}>
							{optionLabel(option)}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{:else if field.type === 'integer' || field.type === 'number'}
			<div class="flex items-center gap-2">
				<Input
					{id}
					type="number"
					class="h-8 w-24 text-sm tabular-nums"
					min={field.minimum ?? undefined}
					max={field.maximum ?? undefined}
					value={String(value ?? field.default ?? '')}
					onchange={(e) => commitNumber(e.currentTarget.value)}
				/>
				{#if field.minimum !== null && field.maximum !== null}
					<span class="text-[10px] text-muted-foreground tabular-nums">
						{field.minimum}–{field.maximum}
					</span>
				{/if}
			</div>
		{:else}
			<Input
				{id}
				class="h-8 w-[240px] font-mono text-xs"
				value={String(value ?? field.default ?? '')}
				oninput={(e) => onChange(e.currentTarget.value)}
				autocomplete="off"
				spellcheck={false}
			/>
		{/if}
	</div>
</Field.Field>
