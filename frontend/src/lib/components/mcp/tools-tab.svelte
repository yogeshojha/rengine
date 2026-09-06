<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { MCP_TOOL_GROUPS, TOUCHES_TARGETS, type McpCapability } from '$lib/types/mcp';

	const tools = $derived(mcp.tools);
	const ceiling = $derived(mcp.status?.ceiling ?? {});

	const grouped = $derived(
		MCP_TOOL_GROUPS.map((group) => ({
			group,
			tools: tools.filter((t) => t.group === group)
		})).filter((entry) => entry.tools.length > 0)
	);

	function args(schema: Record<string, unknown>): { name: string; required: boolean }[] {
		const properties = (schema.properties ?? {}) as Record<string, unknown>;
		const required = new Set((schema.required ?? []) as string[]);
		return Object.keys(properties).map((name) => ({ name, required: required.has(name) }));
	}

	function describe(schema: Record<string, unknown>, key: string): string {
		const properties = (schema.properties ?? {}) as Record<string, { description?: string }>;
		return properties[key]?.description ?? '';
	}
</script>

<div class="space-y-6">
	{#each grouped as entry (entry.group)}
		<Card.Root class="gap-0 py-0">
			<PanelHead title={entry.group}>
				<span>{entry.tools.length} tools</span>
			</PanelHead>
			<div class="divide-y">
				{#each entry.tools as tool (tool.name)}
					{@const available = ceiling[tool.capability] ?? false}
					{@const touches = TOUCHES_TARGETS.includes(tool.capability as McpCapability)}
					<Collapsible.Root>
						<div class="flex flex-wrap items-start justify-between gap-3 px-5 py-3.5">
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-center gap-2">
									<span class="font-mono text-sm font-medium">{tool.name}</span>
									<Badge variant={touches ? 'warning' : 'info'} class="text-[10px] capitalize">
										{tool.capability}
									</Badge>
									{#if tool.destructive}
										<Badge variant="destructive" class="text-[10px]">Destructive</Badge>
									{/if}
									{#if !available}
										<Badge variant="outline" class="gap-1 text-[10px]">
											<TriangleAlertIcon class="size-3" />
											Off for this instance
										</Badge>
									{/if}
								</div>
								<p class="mt-1 text-xs text-muted-foreground">{tool.description}</p>
								<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
									{#each args(tool.schema) as arg (arg.name)}
										<span
											class="rounded border px-1.5 py-0.5 font-mono text-[11px] {arg.required
												? 'border-foreground/25 font-medium'
												: 'text-muted-foreground'}"
										>
											{arg.name}{arg.required ? '' : '?'}
										</span>
									{:else}
										<span class="text-[11px] text-muted-foreground">No arguments</span>
									{/each}
								</div>
							</div>
							<Collapsible.Trigger>
								{#snippet child({ props })}
									<Button {...props} variant="ghost" size="sm" class="shrink-0">
										Arguments
										<ChevronDownIcon class="size-4" />
									</Button>
								{/snippet}
							</Collapsible.Trigger>
						</div>
						<Collapsible.Content>
							<div class="space-y-2 border-t bg-muted/25 px-5 py-3">
								{#each args(tool.schema) as arg (arg.name)}
									<div class="flex gap-3 text-xs">
										<span class="w-32 shrink-0 font-mono">{arg.name}</span>
										<span class="text-muted-foreground">
											{describe(tool.schema, arg.name) || 'No description.'}
										</span>
									</div>
								{:else}
									<p class="text-xs text-muted-foreground">This tool takes no arguments.</p>
								{/each}
								{#if tool.examples.length}
									<div class="pt-1">
										<span
											class="text-[10px] font-semibold tracking-wider uppercase text-muted-foreground"
										>
											Example
										</span>
										{#each tool.examples as example (example)}
											<CodeBlock
												code={example}
												lang="shell"
												toolbar={false}
												numbers={false}
												maxLines={0}
												class="mt-1"
											/>
										{/each}
									</div>
								{/if}
							</div>
						</Collapsible.Content>
					</Collapsible.Root>
				{/each}
			</div>
		</Card.Root>
	{/each}
</div>
