<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import type { SectionField } from '$lib/types/report';

	let {
		field,
		value,
		onChange
	}: {
		field: SectionField;
		value: unknown;
		onChange: (value: unknown) => void;
	} = $props();

	const uid = $props.id();
	const id = $derived(`${uid}-${field.name}`);
	const list = $derived(Array.isArray(value) ? (value as string[]) : []);
	const optionLabel = $derived(
		field.options.find((o) => o.value === String(value ?? ''))?.label ?? String(value ?? '')
	);
	const chips = $derived(field.widget === 'multi' || field.widget === 'columns');
</script>

<div class="min-w-0 py-3">
	{#if field.type === 'flag'}
		<div class="flex items-start justify-between gap-4">
			<div class="min-w-0 space-y-0.5">
				<Label class="text-sm font-normal" for={id}>{field.label}</Label>
				{#if field.help}<p class="text-xs text-muted-foreground">{field.help}</p>{/if}
			</div>
			<span class="flex h-5 shrink-0 items-center">
				<Switch {id} checked={Boolean(value)} onCheckedChange={(v) => onChange(v)} />
			</span>
		</div>
	{:else}
		<div class="space-y-0.5">
			<Label class="text-sm font-normal" for={id}>{field.label}</Label>
			{#if field.help}<p class="text-xs text-muted-foreground">{field.help}</p>{/if}
		</div>
		<div class="mt-2">
			{#if field.widget === 'choice'}
				<Select.Root
					type="single"
					value={String(value ?? '')}
					onValueChange={(v) => v && onChange(v)}
				>
					<Select.Trigger {id} class="h-9 w-full max-w-xs">{optionLabel}</Select.Trigger>
					<Select.Content>
						{#each field.options as option (option.value)}
							<Select.Item value={option.value}>{option.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			{:else if chips}
				<ToggleGroup.Root
					type="multiple"
					variant="outline"
					size="sm"
					spacing={1}
					value={list}
					onValueChange={(v) => onChange(v)}
					class="w-full flex-wrap justify-start"
				>
					{#each field.options as option (option.value)}
						<ToggleGroup.Item value={option.value}>{option.label}</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			{:else if field.widget === 'markdown'}
				<Textarea
					{id}
					value={String(value ?? '')}
					rows={6}
					class="text-xs"
					oninput={(e) => onChange(e.currentTarget.value)}
				/>
			{:else if field.type === 'number'}
				<Input
					{id}
					type="number"
					value={Number(value ?? 0)}
					min={field.minimum ?? undefined}
					max={field.maximum ?? undefined}
					class="h-9 w-28 tabular-nums"
					oninput={(e) => onChange(Number(e.currentTarget.value))}
				/>
			{:else}
				<Input
					{id}
					value={String(value ?? '')}
					class="h-9 max-w-md"
					oninput={(e) => onChange(e.currentTarget.value)}
				/>
			{/if}
		</div>
	{/if}
</div>
