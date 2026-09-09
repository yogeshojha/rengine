<script lang="ts">
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import { Input } from '$lib/components/ui/input';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import type { ToolField, ToolSpec } from '$lib/types/toolbox';

	interface Props {
		tool: ToolSpec;
		values: Record<string, unknown>;
		onChange: (name: string, value: unknown) => void;
	}

	let { tool, values, onChange }: Props = $props();

	const fields = $derived(tool.fields.filter((f) => f.name !== tool.fields[0]?.name));
	const valueOf = (f: ToolField) => values[f.name] ?? f.default;
	const listOf = (f: ToolField) => {
		const v = valueOf(f);
		return Array.isArray(v) ? (v as string[]) : [];
	};
	const optionLabel = (f: ToolField, option: string) => f.option_labels?.[option] ?? option;
</script>

{#if fields.length}
	<Popover.Root>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="size-6 text-muted-foreground"
					aria-label="{tool.title} options"
				>
					<Settings2 class="size-3" />
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content align="end" class="w-72 space-y-3 p-3">
			{#each fields as field (field.name)}
				<div class="space-y-1.5">
					<Label class="text-xs font-normal">{field.title}</Label>
					{#if field.type === 'boolean'}
						<Switch
							checked={Boolean(valueOf(field))}
							onCheckedChange={(v) => onChange(field.name, v)}
						/>
					{:else if field.type === 'array' && field.options}
						<ToggleGroup.Root
							type="multiple"
							variant="outline"
							size="sm"
							spacing={1}
							value={listOf(field)}
							onValueChange={(v) => onChange(field.name, v)}
							class="flex-wrap justify-start"
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
					{:else}
						<Input
							value={String(valueOf(field) ?? '')}
							oninput={(e) => onChange(field.name, e.currentTarget.value)}
							class="h-7 text-xs"
						/>
					{/if}
					{#if field.description}
						<p class="text-[11px] text-muted-foreground">{field.description}</p>
					{/if}
				</div>
			{/each}
		</Popover.Content>
	</Popover.Root>
{/if}
