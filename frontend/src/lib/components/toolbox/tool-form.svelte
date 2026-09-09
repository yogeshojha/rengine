<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Spinner } from '$lib/components/ui/spinner';
	import Play from '@lucide/svelte/icons/play';
	import type { ToolField, ToolSpec } from '$lib/types/toolbox';

	interface Props {
		tool: ToolSpec;
		values: Record<string, unknown>;
		busy: boolean;
		onChange: (name: string, value: unknown) => void;
		onSubmit: () => void;
	}

	let { tool, values, busy, onChange, onSubmit }: Props = $props();

	const primary = $derived(tool.fields.find((f) => f.type === 'string' && f.required));
	const rest = $derived(tool.fields.filter((f) => f !== primary));

	const valueOf = (f: ToolField) => values[f.name] ?? f.default;
	const listOf = (f: ToolField) => {
		const v = valueOf(f);
		return Array.isArray(v) ? (v as string[]) : [];
	};
	const optionLabel = (f: ToolField, option: string) => f.option_labels?.[option] ?? option;

	let input: HTMLInputElement | null = $state(null);
	export function focus() {
		input?.focus();
		input?.select();
	}
</script>

<form
	class="space-y-3"
	onsubmit={(e) => {
		e.preventDefault();
		onSubmit();
	}}
>
	{#if primary}
		<div class="flex items-center gap-2">
			<Input
				bind:ref={input}
				value={String(valueOf(primary) ?? '')}
				oninput={(e) => onChange(primary.name, e.currentTarget.value)}
				placeholder={tool.placeholder || primary.title}
				aria-label={primary.title}
				autocomplete="off"
				autocapitalize="off"
				spellcheck={false}
				class="h-9 font-mono text-sm"
			/>
			<Button type="submit" size="sm" class="h-9 shrink-0 px-4" disabled={busy}>
				{#if busy}
					<Spinner class="size-3.5" />
				{:else}
					<Play class="size-3.5" />
				{/if}
				Run
			</Button>
		</div>
	{/if}

	{#if rest.length}
		<div class="flex flex-wrap items-center gap-x-5 gap-y-2">
			{#each rest as field (field.name)}
				{#if field.type === 'boolean'}
					<div class="flex items-center gap-2">
						<Switch
							id="tb-{tool.name}-{field.name}"
							checked={Boolean(valueOf(field))}
							onCheckedChange={(v) => onChange(field.name, v)}
						/>
						<Label for="tb-{tool.name}-{field.name}" class="text-xs font-normal">
							{field.title}
						</Label>
					</div>
				{:else if field.type === 'array' && field.options}
					<div class="flex items-center gap-2">
						<span class="text-xs text-muted-foreground">{field.title}</span>
						<ToggleGroup.Root
							type="multiple"
							variant="outline"
							size="sm"
							spacing={1}
							value={listOf(field)}
							onValueChange={(v) => onChange(field.name, v)}
							class="flex-wrap"
							aria-label={field.title}
						>
							{#each field.options as option (option)}
								<ToggleGroup.Item
									value={option}
									class="h-6 px-2 text-[11px] font-normal data-[state=on]:bg-foreground data-[state=on]:text-background"
								>
									{optionLabel(field, option)}
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</div>
				{:else if field.type === 'integer' || field.type === 'number'}
					<div class="flex items-center gap-2">
						<Label for="tb-{tool.name}-{field.name}" class="text-xs font-normal">
							{field.title}
						</Label>
						<Input
							id="tb-{tool.name}-{field.name}"
							type="number"
							min={field.minimum ?? undefined}
							max={field.maximum ?? undefined}
							value={String(valueOf(field) ?? '')}
							oninput={(e) => onChange(field.name, Number(e.currentTarget.value))}
							class="h-7 w-24 text-xs"
						/>
					</div>
				{:else}
					<div class="flex items-center gap-2">
						<Label for="tb-{tool.name}-{field.name}" class="text-xs font-normal">
							{field.title}
						</Label>
						<Input
							id="tb-{tool.name}-{field.name}"
							value={String(valueOf(field) ?? '')}
							oninput={(e) => onChange(field.name, e.currentTarget.value)}
							class="h-7 w-48 text-xs"
						/>
					</div>
				{/if}
			{/each}
		</div>
	{/if}
</form>
