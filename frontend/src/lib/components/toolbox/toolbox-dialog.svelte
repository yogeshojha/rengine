<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import ToolList from './tool-list.svelte';
	import ToolForm from './tool-form.svelte';
	import RunResult from './run-result.svelte';
	import RecentRuns from './recent-runs.svelte';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { toolIcon } from '$lib/config/toolbox';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { toast } from 'svelte-sonner';
	import { untrack } from 'svelte';
	import type { ToolRun } from '$lib/types/toolbox';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	let selected = $state<string | null>(null);
	let values = $state<Record<string, Record<string, unknown>>>({});
	let shown = $state<Record<string, string>>({});
	let form: ReturnType<typeof ToolForm> | null = $state(null);

	const tool = $derived(selected ? toolbox.tool(selected) : undefined);
	const Icon = $derived(tool ? toolIcon(tool.icon) : null);
	const run = $derived.by(() => {
		if (!selected) return undefined;
		const id = shown[selected];
		return id ? toolbox.runs.find((r) => r.id === id) : toolbox.lastRun(selected);
	});

	$effect(() => {
		if (!open) return;
		void toolbox.load();
		const names = toolbox.tools.map((t) => t.name);
		if (!names.length) return;
		const stored = localStorage.getItem(STORAGE_KEYS.toolboxLastTool);
		untrack(() => {
			if (selected && names.includes(selected)) return;
			selected = stored && names.includes(stored) ? stored : names[0];
		});
	});

	$effect(() => {
		if (!open || !tool) return;
		localStorage.setItem(STORAGE_KEYS.toolboxLastTool, tool.name);
		untrack(() => queueMicrotask(() => form?.focus()));
	});

	function select(name: string) {
		selected = name;
	}

	function change(name: string, value: unknown) {
		if (!selected) return;
		values = { ...values, [selected]: { ...(values[selected] ?? {}), [name]: value } };
	}

	function payload(): Record<string, unknown> {
		if (!tool) return {};
		const current = values[tool.name] ?? {};
		const out: Record<string, unknown> = {};
		for (const field of tool.fields) {
			const value = current[field.name] ?? field.default;
			if (value !== null && value !== undefined && value !== '') out[field.name] = value;
		}
		return out;
	}

	async function submit() {
		if (!tool || toolbox.running) return;
		try {
			const started = await toolbox.run(tool.name, payload(), projectsStore.activeProject?.id);
			shown = { ...shown, [tool.name]: started.id };
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'The run could not be started');
		}
	}

	function openRun(previous: ToolRun) {
		selected = previous.tool;
		shown = { ...shown, [previous.tool]: previous.id };
		values = { ...values, [previous.tool]: { ...previous.input } };
	}

	async function clearHistory() {
		await toolbox.clear();
		shown = {};
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="max-h-[88vh] gap-0 overflow-hidden p-0 sm:max-w-4xl">
		<Dialog.Header class="border-b px-4 py-2.5">
			<Dialog.Title class="text-sm font-medium">Toolbox</Dialog.Title>
			<Dialog.Description class="sr-only">
				Lookup, discovery and intelligence tools
			</Dialog.Description>
		</Dialog.Header>

		<div class="grid h-[70vh] min-h-0 grid-cols-1 md:grid-cols-[13.5rem_minmax(0,1fr)]">
			<aside class="hidden min-h-0 min-w-0 flex-col border-r md:flex">
				{#if toolbox.loadingCatalog && !toolbox.tools.length}
					<div class="flex flex-1 items-center justify-center">
						<Spinner class="size-4 text-muted-foreground" />
					</div>
				{:else}
					<ToolList tools={toolbox.tools} groups={toolbox.groups} {selected} onSelect={select} />
					<RecentRuns
						runs={toolbox.runs}
						activeId={run?.id ?? null}
						onOpen={openRun}
						onClear={clearHistory}
					/>
				{/if}
			</aside>

			<section class="flex min-h-0 min-w-0 flex-col">
				{#if tool}
					<div class="space-y-2.5 border-b px-4 py-3">
						<div class="flex items-start gap-2">
							{#if Icon}
								<span class="flex h-5 shrink-0 items-center"><Icon class="size-4" /></span>
							{/if}
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<h3 class="text-sm leading-5 font-medium">{tool.title}</h3>
									{#if tool.touches_target}
										<Hint text="Sends a request to the named host">
											{#snippet child(props)}
												<span {...props} class="inline-flex">
													<Badge variant="warning" class="h-4 px-1.5 text-[10px]">
														Sends traffic
													</Badge>
												</span>
											{/snippet}
										</Hint>
									{/if}
								</div>
								<p class="text-xs leading-snug text-muted-foreground">{tool.description}</p>
							</div>
						</div>
						<ToolForm
							bind:this={form}
							{tool}
							values={values[tool.name] ?? {}}
							busy={toolbox.running}
							onChange={change}
							onSubmit={submit}
						/>
					</div>
					<ScrollArea class="min-h-0 flex-1">
						<div class="px-4 py-3">
							{#if run}
								<RunResult {run} onNavigate={() => (open = false)} />
							{:else if tool.examples.length}
								<p class="py-4 text-[13px] text-muted-foreground">
									Examples: {tool.examples.join(', ')}
								</p>
							{/if}
						</div>
					</ScrollArea>
				{:else}
					<div class="flex flex-1 items-center justify-center">
						<Spinner class="size-4 text-muted-foreground" />
					</div>
				{/if}
			</section>
		</div>
	</Dialog.Content>
</Dialog.Root>
