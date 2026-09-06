<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
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

	const list = $derived(Array.isArray(value) ? (value as string[]) : []);
	const optionLabel = $derived(
		field.options.find((o) => o.value === String(value ?? ''))?.label ?? String(value ?? '')
	);

	function toggle(option: string) {
		onChange(list.includes(option) ? list.filter((v) => v !== option) : [...list, option]);
	}
</script>

<div class="space-y-1.5">
	{#if field.type === 'flag'}
		<div class="flex items-start justify-between gap-4">
			<div class="space-y-0.5">
				<Label class="text-sm">{field.label}</Label>
				{#if field.help}<p class="text-xs text-muted-foreground">{field.help}</p>{/if}
			</div>
			<Switch checked={Boolean(value)} onCheckedChange={(v) => onChange(v)} />
		</div>
	{:else}
		<Label class="text-xs">{field.label}</Label>
		{#if field.widget === 'choice'}
			<Select.Root
				type="single"
				value={String(value ?? '')}
				onValueChange={(v) => v && onChange(v)}
			>
				<Select.Trigger class="h-9 w-full">{optionLabel}</Select.Trigger>
				<Select.Content>
					{#each field.options as option (option.value)}
						<Select.Item value={option.value}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{:else if field.widget === 'multi' || field.widget === 'columns'}
			<div class="flex flex-wrap gap-1.5">
				{#each field.options as option (option.value)}
					<button
						type="button"
						class="rounded-md border px-2 py-1 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
						data-active={list.includes(option.value)}
						onclick={() => toggle(option.value)}
					>
						{option.label}
					</button>
				{/each}
			</div>
		{:else if field.widget === 'markdown'}
			<Textarea
				value={String(value ?? '')}
				rows={6}
				class="text-xs"
				oninput={(e) => onChange(e.currentTarget.value)}
			/>
		{:else if field.type === 'number'}
			<Input
				type="number"
				value={Number(value ?? 0)}
				min={field.minimum ?? undefined}
				max={field.maximum ?? undefined}
				class="h-9"
				oninput={(e) => onChange(Number(e.currentTarget.value))}
			/>
		{:else}
			<Input
				value={String(value ?? '')}
				class="h-9"
				oninput={(e) => onChange(e.currentTarget.value)}
			/>
		{/if}
		{#if field.help}
			<p class="text-xs text-muted-foreground">{field.help}</p>
		{/if}
	{/if}
</div>
