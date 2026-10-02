<script lang="ts">
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import CodeBlock from '$lib/components/code-block.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { contextLabel, schemaArgs } from '$lib/utilities/mcp';
	import {
		MCP_CAPABILITIES,
		MCP_CAPABILITY_LABELS,
		TOUCHES_TARGETS,
		type McpCapability,
		type McpTool
	} from '$lib/types/mcp';

	interface Props {
		open: boolean;
		tools: McpTool[];
		ceiling: Record<string, boolean>;
	}

	let { open = $bindable(), tools, ceiling }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';

	let selected = $state<string | null>(null);

	const groups = $derived(
		MCP_CAPABILITIES.map((cap) => {
			const rows = tools.filter((t) => t.capability === cap);
			return {
				cap,
				rows,
				on: ceiling[cap] ?? false,
				context: rows.reduce((n, t) => n + t.context_tokens, 0)
			};
		}).filter((g) => g.rows.length)
	);
	const ordered = $derived(groups.flatMap((g) => g.rows));
	const index = $derived(ordered.findIndex((t) => t.name === selected));
	const tool = $derived(index >= 0 ? ordered[index] : null);
	const args = $derived(tool ? schemaArgs(tool.schema) : []);
	const touches = $derived(
		tool ? TOUCHES_TARGETS.includes(tool.capability as McpCapability) : false
	);

	function step(dir: -1 | 1) {
		const next = ordered[index + dir];
		if (next) selected = next.name;
	}

	function onKeydown(e: KeyboardEvent) {
		if (!open || !tool) return;
		if (e.key === 'ArrowDown' || e.key === 'j') {
			e.preventDefault();
			step(1);
		} else if (e.key === 'ArrowUp' || e.key === 'k') {
			e.preventDefault();
			step(-1);
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

<Sheet.Root
	bind:open
	onOpenChange={(v) => {
		if (!v) selected = null;
	}}
>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if tool}
			<Sheet.Header class="gap-2 border-b px-5 py-4">
				<div class="flex flex-wrap items-center gap-2 pr-6">
					<Button
						variant="ghost"
						size="icon"
						class="-ml-1 size-7"
						onclick={() => (selected = null)}
					>
						<ArrowLeft class="size-4" />
						<span class="sr-only">All tools</span>
					</Button>
					<Sheet.Title class="font-mono text-base">{tool.name}</Sheet.Title>
					<Badge variant={touches ? 'warning' : 'secondary'} class="text-2xs">
						{MCP_CAPABILITY_LABELS[tool.capability as McpCapability]}
					</Badge>
					{#if tool.destructive}
						<Badge variant="destructive" class="text-2xs">Destructive</Badge>
					{/if}
					{#if !(ceiling[tool.capability] ?? false)}
						<Badge variant="outline" class="border-dashed text-2xs">Off</Badge>
					{/if}
				</div>
				<Sheet.Description>
					{tool.title} · {contextLabel(tool.context_tokens)} context tokens
				</Sheet.Description>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 px-5 py-5">
					<p class="text-sm leading-relaxed whitespace-pre-line">{tool.description}</p>

					<section class="flex flex-col gap-2">
						<SectionHead title="Arguments" count={args.length} />
						{#if args.length}
							<div class="divide-y rounded-md border">
								{#each args as arg (arg.name)}
									<div class="flex flex-col gap-1 px-3 py-2.5">
										<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
											<span class="font-mono text-sm font-medium">{arg.name}</span>
											<span class="font-mono text-2xs text-muted-foreground">{arg.type}</span>
											{#if arg.required}
												<span class="text-2xs font-medium text-foreground/80">required</span>
											{:else if arg.fallback !== null}
												<span class="font-mono text-2xs text-muted-foreground">
													default {arg.fallback}
												</span>
											{/if}
										</div>
										{#if arg.description}
											<p class="text-xs leading-snug text-muted-foreground">{arg.description}</p>
										{/if}
										{#if arg.options.length}
											<div class="flex flex-wrap gap-1">
												{#each arg.options as option (option)}
													<span class="rounded border px-1.5 py-px font-mono text-2xs"
														>{option}</span
													>
												{/each}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-sm text-muted-foreground">No arguments.</p>
						{/if}
					</section>

					{#if tool.examples.length}
						<section class="flex flex-col gap-2">
							<SectionHead title="Examples" />
							<div class="flex flex-col gap-2">
								{#each tool.examples as example (example)}
									<CodeBlock code={example} lang="shell" numbers={false} maxLines={0} />
								{/each}
							</div>
						</section>
					{/if}
				</div>
			</ScrollArea>

			<div
				class="flex items-center justify-between border-t px-5 py-3 text-xs text-muted-foreground"
			>
				<span class="tabular-nums">{index + 1} of {ordered.length}</span>
				<div class="flex items-center gap-1">
					<Button
						variant="ghost"
						size="icon"
						class="size-7"
						disabled={index <= 0}
						onclick={() => step(-1)}
					>
						<ChevronUp class="size-4" />
						<span class="sr-only">Previous tool</span>
					</Button>
					<Button
						variant="ghost"
						size="icon"
						class="size-7"
						disabled={index >= ordered.length - 1}
						onclick={() => step(1)}
					>
						<ChevronDown class="size-4" />
						<span class="sr-only">Next tool</span>
					</Button>
					<Kbd class="ml-1">j</Kbd>
					<Kbd>k</Kbd>
				</div>
			</div>
		{:else}
			<Sheet.Header class="border-b px-5 py-4">
				<Sheet.Title>Tools</Sheet.Title>
				<Sheet.Description class="tabular-nums">
					{tools.length} tools
				</Sheet.Description>
			</Sheet.Header>
			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col divide-y px-5">
					{#each groups as group (group.cap)}
						<section class="flex flex-col gap-1.5 py-4 {group.on ? '' : 'opacity-50'}">
							<h4 class="flex items-baseline gap-2 {LABEL}">
								<span class={TOUCHES_TARGETS.includes(group.cap) ? 'text-warning' : ''}>
									{MCP_CAPABILITY_LABELS[group.cap]}
								</span>
								<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
									{group.rows.length} · {contextLabel(group.context)} context tokens{group.on
										? ''
										: ' · off'}
								</span>
							</h4>
							<ul class="flex flex-col">
								{#each group.rows as row (row.name)}
									<li>
										<button
											type="button"
											class="flex w-full items-baseline gap-2 rounded px-1 py-1 text-left leading-5 hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
											onclick={() => (selected = row.name)}
										>
											<code class="shrink-0 font-mono text-xs">{row.name}</code>
											<span class="min-w-0 text-xs text-muted-foreground">{row.title}</span>
										</button>
									</li>
								{/each}
							</ul>
						</section>
					{/each}
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
