<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { Alert, AlertDescription, AlertTitle } from '$lib/components/ui/alert';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import SectionHead from '$lib/components/section-head.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import Terminal from '@lucide/svelte/icons/terminal';
	import { phaseLabel, type ToolOption } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		toolOptions: Record<string, string>;
		tools: ToolOption[];
		readonly?: boolean;
		onOpenChange: (open: boolean) => void;
		onChange: (toolOptions: Record<string, string>) => void;
	}

	let { open, toolOptions, tools, readonly = false, onOpenChange, onChange }: Props = $props();

	let options = $derived(toolOptions ?? {});
	let phases = $derived([...new Set(tools.map((t) => t.phase))]);

	function handleInput(name: string, value: string) {
		const next = { ...options };
		if (value.trim()) next[name] = value;
		else delete next[name];
		onChange(next);
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title class="flex items-center gap-2 text-base">
				<Terminal size={16} class="text-muted-foreground" />
				Tool arguments
			</Sheet.Title>
			<Sheet.Description>Extra CLI flags appended to each tool command.</Sheet.Description>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="space-y-5 px-5 py-4">
				<Alert class="border-warning/30 bg-warning/5 text-warning">
					<AlertTriangle class="size-4" />
					<AlertTitle>Advanced</AlertTitle>
					<AlertDescription class="text-warning/90">
						An invalid flag fails the tool and its stage.
					</AlertDescription>
				</Alert>

				{#each phases as phase (phase)}
					<section class="flex flex-col gap-4">
						<SectionHead title={phaseLabel(phase)} />
						{#each tools.filter((t) => t.phase === phase) as tool (tool.name)}
							<FormField label={tool.label}>
								{#snippet children({ id })}
									<Input
										{id}
										value={options[tool.name] ?? ''}
										{readonly}
										oninput={(e) => handleInput(tool.name, e.currentTarget.value)}
										placeholder={tool.example}
										class="font-mono text-xs"
										autocomplete="off"
										autocapitalize="off"
										spellcheck={false}
									/>
								{/snippet}
							</FormField>
						{/each}
					</section>
				{/each}
			</div>
		</ScrollArea>
		{#if readonly}
			<p class="border-t px-5 py-3 text-xs text-muted-foreground">Editable by administrators.</p>
		{/if}
	</Sheet.Content>
</Sheet.Root>
