<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Check from '@lucide/svelte/icons/check';
	import { untrack } from 'svelte';

	import * as Breadcrumb from '$lib/components/ui/breadcrumb';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import type { TreeNode } from '$lib/utilities/endpoints';

	interface Props {
		host: string;
		ranked: TreeNode[];
		offset?: number;
		total?: number;
		onLeave: () => void;
		onSwitch: (host: string) => void;
		onStep: (dir: -1 | 1) => void;
		search: (term: string) => Promise<TreeNode[]>;
	}

	let { host, ranked, offset = 0, total = 0, onLeave, onSwitch, onStep, search }: Props = $props();

	let open = $state(false);
	let term = $state('');
	let remote = $state<TreeNode[] | null>(null);
	let searching = $state(false);
	let req = 0;

	let at = $derived(ranked.findIndex((n) => n.name === host));
	let position = $derived(at >= 0 ? offset + at + 1 : 0);
	let local = $derived(
		term.trim()
			? ranked.filter((n) => n.name.toLowerCase().includes(term.trim().toLowerCase()))
			: ranked
	);
	let options = $derived(remote ?? local);

	$effect(() => {
		const needle = term.trim();
		if (needle.length < 2 || local.length) {
			remote = null;
			return;
		}
		const my = ++req;
		const handle = setTimeout(async () => {
			searching = true;
			try {
				const res = await untrack(() => search(needle));
				if (my === req) remote = res;
			} catch {
				if (my === req) remote = [];
			} finally {
				if (my === req) searching = false;
			}
		}, SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(handle);
	});

	function pick(name: string) {
		open = false;
		term = '';
		if (name !== host) onSwitch(name);
	}
</script>

<div class="flex min-w-0 items-center gap-2 px-4 py-2 text-sm">
	<Breadcrumb.Root class="min-w-0">
		<Breadcrumb.List class="flex-nowrap sm:gap-1.5">
			<Breadcrumb.Item>
				<button
					type="button"
					class="rounded-sm transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					onclick={onLeave}
				>
					Hosts
				</button>
			</Breadcrumb.Item>
			<Breadcrumb.Separator />
			<Breadcrumb.Item class="min-w-0">
				<Popover.Root bind:open>
					<Popover.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="flex min-w-0 items-center gap-1.5 rounded-md border bg-card px-2 py-1 font-mono text-sm font-medium text-foreground hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
								aria-label="Switch host"
							>
								<span class="truncate">{host}</span>
								<ChevronDown class="size-3.5 shrink-0 text-muted-foreground" />
							</button>
						{/snippet}
					</Popover.Trigger>
					<Popover.Content class="w-96 p-0" align="start">
						<Command.Root shouldFilter={false}>
							<Command.Input placeholder="Find a host…" bind:value={term} />
							<Command.List class="max-h-none overflow-visible">
								<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
									{#if searching}
										<Command.Loading>Searching…</Command.Loading>
									{:else if options.length === 0}
										<Command.Empty>No host matches.</Command.Empty>
									{/if}
									<Command.Group>
										{#each options as n (n.key)}
											<Command.Item value={n.name} onSelect={() => pick(n.name)} class="gap-2">
												<Check
													class="size-3.5 shrink-0 {n.name === host ? 'opacity-100' : 'opacity-0'}"
												/>
												<span class="min-w-0 flex-1 truncate font-mono text-xs">{n.name}</span>
												<span class="text-xs tabular-nums text-muted-foreground">
													{n.subtree_count.toLocaleString()}
												</span>
											</Command.Item>
										{/each}
									</Command.Group>
								</ScrollArea>
							</Command.List>
						</Command.Root>
					</Popover.Content>
				</Popover.Root>
			</Breadcrumb.Item>
		</Breadcrumb.List>
	</Breadcrumb.Root>

	<div class="ml-auto flex shrink-0 items-center gap-1">
		{#if position > 0 && total > 0}
			<span class="text-xs tabular-nums text-muted-foreground">
				{position.toLocaleString()} of {total.toLocaleString()}
			</span>
		{/if}
		<Hint text="Previous host  [">
			{#snippet child(props)}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="size-7"
					aria-label="Previous host"
					disabled={position <= 1}
					onclick={() => onStep(-1)}
				>
					<ChevronLeft class="size-4" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Next host  ]">
			{#snippet child(props)}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="size-7"
					aria-label="Next host"
					disabled={position === 0 || position >= total}
					onclick={() => onStep(1)}
				>
					<ChevronRight class="size-4" />
				</Button>
			{/snippet}
		</Hint>
	</div>
</div>
