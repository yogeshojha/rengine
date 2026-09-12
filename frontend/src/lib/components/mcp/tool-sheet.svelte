<script lang="ts">
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CapabilityChips from './capability-chips.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { durationLabel, median, schemaArgs } from '$lib/utilities/mcp';
	import { TOUCHES_TARGETS, type McpCall, type McpCapability, type McpTool } from '$lib/types/mcp';

	interface Props {
		tool: McpTool | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		ceiling: Record<string, boolean>;
		calls: McpCall[];
		index: number;
		total: number;
		onStep: (dir: -1 | 1) => void;
		canAdmin: boolean;
		onCeiling: () => void;
	}

	let {
		tool,
		open,
		onOpenChange,
		ceiling,
		calls,
		index,
		total,
		onStep,
		canAdmin,
		onCeiling
	}: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';

	const args = $derived(tool ? schemaArgs(tool.schema) : []);
	const available = $derived(tool ? (ceiling[tool.capability] ?? false) : true);
	const touches = $derived(
		tool ? TOUCHES_TARGETS.includes(tool.capability as McpCapability) : false
	);
	const own = $derived(tool ? calls.filter((c) => c.tool === tool.name) : []);
	const failed = $derived(own.filter((c) => !c.ok).length);
	const typical = $derived(median(own.map((c) => c.duration_ms)));
	const lastFailure = $derived(own.find((c) => !c.ok && c.detail) ?? null);

	function onKeydown(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'ArrowDown' || e.key === 'j') {
			e.preventDefault();
			onStep(1);
		} else if (e.key === 'ArrowUp' || e.key === 'k') {
			e.preventDefault();
			onStep(-1);
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if tool}
			<Sheet.Header class="gap-2 border-b px-6 pt-6 pb-4">
				<div class="flex flex-wrap items-center gap-2 pr-6">
					<Sheet.Title class="font-mono text-base">{tool.name}</Sheet.Title>
					<CapabilityChips granted={[tool.capability]} />
					{#if tool.destructive}
						<Badge variant="destructive" class="text-2xs">Destructive</Badge>
					{/if}
				</div>
				<Sheet.Description>{tool.title}</Sheet.Description>
				{#if !available}
					<div
						class="flex flex-wrap items-center justify-between gap-2 rounded-md border border-dashed px-3 py-2 text-xs"
					>
						<span class="flex items-center gap-1.5 text-muted-foreground">
							<TriangleAlertIcon class="size-3.5" />
							Off for this instance. No token can call it while its capability is below the ceiling.
						</span>
						{#if canAdmin}
							<Button variant="outline" size="sm" class="h-6 text-xs" onclick={onCeiling}>
								Change the ceiling
							</Button>
						{/if}
					</div>
				{:else if touches}
					<div
						class="flex items-center gap-1.5 rounded-md border border-warning/30 bg-warning/6 px-3 py-2 text-xs text-warning"
					>
						<TriangleAlertIcon class="size-3.5" />
						Sends traffic to the target.
					</div>
				{/if}
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 px-6 py-5">
					<section class="flex flex-col gap-2">
						<h4 class={LABEL}>Description</h4>
						<p class="text-sm leading-relaxed whitespace-pre-line">{tool.description}</p>
					</section>

					<section class="flex flex-col gap-2">
						<h4 class="flex items-baseline gap-2 {LABEL}">
							Arguments
							<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
								{args.length}
							</span>
						</h4>
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
							<p class="text-sm text-muted-foreground">This tool takes no arguments.</p>
						{/if}
					</section>

					{#if tool.examples.length}
						<section class="flex flex-col gap-2">
							<h4 class={LABEL}>Examples</h4>
							<div class="flex flex-col gap-2">
								{#each tool.examples as example (example)}
									<CodeBlock code={example} lang="shell" numbers={false} maxLines={0} />
								{/each}
							</div>
						</section>
					{/if}

					<section class="flex flex-col gap-2">
						<h4 class="flex items-baseline gap-2 {LABEL}">
							Recent calls
							<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
								{own.length}
							</span>
						</h4>
						{#if own.length}
							<div class="grid grid-cols-3 divide-x rounded-md border text-sm">
								<div class="flex flex-col gap-0.5 px-3 py-2">
									<span class="text-2xs text-muted-foreground">Failed</span>
									<span class="tabular-nums {failed ? 'text-destructive' : ''}">{failed}</span>
								</div>
								<div class="flex flex-col gap-0.5 px-3 py-2">
									<span class="text-2xs text-muted-foreground">Typical</span>
									<span class="tabular-nums">{typical === null ? '—' : durationLabel(typical)}</span
									>
								</div>
								<div class="flex flex-col gap-0.5 px-3 py-2">
									<span class="text-2xs text-muted-foreground">Last</span>
									<span>{relativeTime(own[0].at)}</span>
								</div>
							</div>
							{#if lastFailure}
								<p class="border-l-2 border-destructive/40 pl-3 text-xs text-muted-foreground">
									<span class="text-destructive">Last failure</span>
									{relativeTime(lastFailure.at)} · {lastFailure.detail}
								</p>
							{/if}
						{:else}
							<p class="text-sm text-muted-foreground">No calls in the recent trail.</p>
						{/if}
					</section>
				</div>
			</ScrollArea>

			{#if total > 1}
				<div
					class="flex items-center justify-between border-t px-6 py-3 text-xs text-muted-foreground"
				>
					<span class="tabular-nums">{index + 1} of {total}</span>
					<div class="flex items-center gap-1">
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index <= 0}
							onclick={() => onStep(-1)}
						>
							<ChevronUp class="size-4" />
							<span class="sr-only">Previous tool</span>
						</Button>
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index >= total - 1}
							onclick={() => onStep(1)}
						>
							<ChevronDown class="size-4" />
							<span class="sr-only">Next tool</span>
						</Button>
						<Kbd class="ml-1">j</Kbd>
						<Kbd>k</Kbd>
					</div>
				</div>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>
