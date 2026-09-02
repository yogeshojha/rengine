<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { Alert, AlertDescription, AlertTitle } from '$lib/components/ui/alert';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import Terminal from '@lucide/svelte/icons/terminal';
	import type { ToolOption } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		toolOptions: Record<string, string>;
		tools: ToolOption[];
		onOpenChange: (open: boolean) => void;
		onChange: (toolOptions: Record<string, string>) => void;
	}

	let { open, toolOptions, tools, onOpenChange, onChange }: Props = $props();

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
	<Sheet.Content side="right" class="flex w-[calc(100%-2rem)] flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title class="flex items-center gap-2 text-base">
				<Terminal size={16} class="text-muted-foreground" />
				Tool Arguments
			</Sheet.Title>
			<Sheet.Description>Extra CLI flags appended to each tool when a scan runs.</Sheet.Description>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="space-y-5 px-5 py-4">
				<Alert class="border-warning/30 bg-warning/5 text-warning">
					<AlertTriangle class="size-4" />
					<AlertTitle>Advanced</AlertTitle>
					<AlertDescription class="text-warning/90">
						These flags are appended to each tool's command exactly as written. reNgine does not
						validate them: invalid, unsupported, or conflicting flags can make a tool error out or
						cause the scan stage to fail. Leave blank unless you know the tool's CLI. Arguments are
						passed safely (never shell-interpreted).
					</AlertDescription>
				</Alert>

				{#each phases as phase (phase)}
					<div class="space-y-3">
						<h4 class="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
							{phase}
						</h4>
						{#each tools.filter((t) => t.phase === phase) as tool (tool.name)}
							<div class="space-y-1.5">
								<Label for="tool-opt-{tool.name}" class="text-sm">{tool.label}</Label>
								<Input
									id="tool-opt-{tool.name}"
									value={options[tool.name] ?? ''}
									oninput={(e) => handleInput(tool.name, e.currentTarget.value)}
									placeholder={tool.example}
									class="font-mono text-xs"
									autocomplete="off"
									autocapitalize="off"
									spellcheck={false}
								/>
							</div>
						{/each}
					</div>
				{/each}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>
