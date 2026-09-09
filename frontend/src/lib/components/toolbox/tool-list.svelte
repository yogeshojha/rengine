<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Input } from '$lib/components/ui/input';
	import Search from '@lucide/svelte/icons/search';
	import Hint from '$lib/components/hint.svelte';
	import { MODE_CLASS, MODE_HELP, MODE_LABELS, toolIcon, toolMode } from '$lib/config/toolbox';
	import { cn } from '$lib/utils';
	import type { ToolGroupSpec, ToolSpec } from '$lib/types/toolbox';

	interface Props {
		tools: ToolSpec[];
		groups: ToolGroupSpec[];
		selected: string | null;
		onSelect: (name: string) => void;
	}

	let { tools, groups, selected, onSelect }: Props = $props();

	let query = $state('');

	const matches = $derived.by(() => {
		const term = query.trim().toLowerCase();
		if (!term) return tools;
		return tools.filter((t) =>
			[t.title, t.description, t.name, ...t.examples].join(' ').toLowerCase().includes(term)
		);
	});

	const sections = $derived(
		groups
			.map((group) => ({ group, items: matches.filter((t) => t.group === group.key) }))
			.filter((s) => s.items.length > 0)
	);
</script>

<div class="border-b p-2">
	<div class="relative">
		<Search
			class="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
		/>
		<Input
			bind:value={query}
			placeholder="Find a tool"
			aria-label="Find a tool"
			class="h-8 pl-7 text-xs"
			autocomplete="off"
			spellcheck={false}
		/>
	</div>
</div>

<ScrollArea class="min-h-0 flex-1">
	<div class="space-y-3 p-2">
		{#each sections as section (section.group.key)}
			<div>
				<p class="px-2 pb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
					{section.group.label}
				</p>
				{#each section.items as tool (tool.name)}
					{@const Icon = toolIcon(tool.icon)}
					{@const mode = toolMode(tool.touches_target)}
					<Hint text={MODE_HELP[mode]}>
						{#snippet child(hintProps)}
							<button
								{...hintProps}
								type="button"
								onclick={() => onSelect(tool.name)}
								class={cn(
									'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] transition-colors',
									selected === tool.name
										? 'bg-accent text-accent-foreground'
										: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
								)}
							>
								<Icon class="size-3.5 shrink-0" />
								<span class="min-w-0 flex-1 truncate">{tool.title}</span>
								<span class="shrink-0 text-[10px] {MODE_CLASS[mode]}">{MODE_LABELS[mode]}</span>
							</button>
						{/snippet}
					</Hint>
				{/each}
			</div>
		{:else}
			<p class="px-2 py-6 text-center text-xs text-muted-foreground">No matching tool</p>
		{/each}
	</div>
</ScrollArea>
