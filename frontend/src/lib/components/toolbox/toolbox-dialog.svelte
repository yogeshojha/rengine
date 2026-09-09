<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import RunSection from './run-section.svelte';
	import ToolOptions from './tool-options.svelte';
	import Search from '@lucide/svelte/icons/search';
	import Plus from '@lucide/svelte/icons/plus';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { toolIcon } from '$lib/config/toolbox';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { relativeTime } from '$lib/utilities/dates';
	import { untrack } from 'svelte';
	import type { ToolRun } from '$lib/types/toolbox';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	let query = $state('');
	let options = $state<Record<string, Record<string, unknown>>>({});
	let field: HTMLInputElement | null = $state(null);

	const projectId = $derived(projectsStore.activeProject?.id);
	const subject = $derived(toolbox.subject);
	const offered = $derived(
		(subject?.offered ?? []).map((n) => toolbox.tool(n)).filter((t) => t !== undefined)
	);
	const recent = $derived.by(() => {
		const seen: Record<string, true> = {};
		return toolbox.history
			.filter((r) => {
				if (seen[r.label]) return false;
				seen[r.label] = true;
				return true;
			})
			.slice(0, 8);
	});
	const examples = $derived([...new Set(toolbox.tools.flatMap((t) => t.examples))].slice(0, 5));

	$effect(() => {
		if (!open) return;
		void toolbox.load();
		untrack(() => queueMicrotask(() => field?.focus()));
	});

	function submit(value?: string) {
		const q = (value ?? query).trim();
		if (!q || toolbox.busy) return;
		query = q;
		localStorage.setItem(STORAGE_KEYS.toolboxLastQuery, q);
		void toolbox.lookup(q, projectId);
	}

	function chase(value: string, tool: string | null) {
		if (tool) {
			query = value;
			void toolbox.add(tool, { [valueField(tool)]: value, ...(options[tool] ?? {}) }, projectId);
			return;
		}
		submit(value);
	}

	function valueField(tool: string): string {
		return toolbox.tool(tool)?.fields[0]?.name ?? 'query';
	}

	function addTool(name: string) {
		if (!subject) return;
		void toolbox.add(
			name,
			{ [valueField(name)]: subject.value, ...(options[name] ?? {}) },
			projectId
		);
	}

	function setOption(tool: string, key: string, value: unknown) {
		options = { ...options, [tool]: { ...(options[tool] ?? {}), [key]: value } };
	}

	function replay(run: ToolRun) {
		query = run.label;
		toolbox.show(run);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="max-h-[88vh] gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b py-3 pr-12 pl-4">
			<Dialog.Title class="sr-only">Toolbox</Dialog.Title>
			<Dialog.Description class="sr-only">
				Lookup, discovery and intelligence tools
			</Dialog.Description>
			<form
				class="flex items-center gap-2"
				onsubmit={(e) => {
					e.preventDefault();
					submit();
				}}
			>
				<div class="relative flex-1">
					<Search
						class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
					/>
					<Input
						bind:ref={field}
						bind:value={query}
						placeholder="Domain, address, range, URL, AS or CVE"
						aria-label="Value to look up"
						autocomplete="off"
						autocapitalize="off"
						spellcheck={false}
						class="h-9 pl-8 font-mono text-sm"
					/>
				</div>
				<Button type="submit" size="sm" class="h-9 shrink-0 px-4" disabled={toolbox.busy}>
					{#if toolbox.busy}<Spinner class="size-3.5" />{/if}
					Look up
				</Button>
			</form>
		</Dialog.Header>

		<ScrollArea class="h-[70vh] min-h-0">
			<div class="space-y-6 px-4 py-4">
				{#if toolbox.error}
					<div
						class="flex items-start gap-2 rounded-md border border-warning/25 bg-warning/10 px-3 py-2.5 text-[13px] leading-5 text-warning"
					>
						<span class="flex h-5 shrink-0 items-center"><TriangleAlert class="size-4" /></span>
						<span class="min-w-0">{toolbox.error}</span>
					</div>
				{/if}

				{#if subject && toolbox.runs.length}
					<div class="flex flex-wrap items-center gap-2 border-b pb-3">
						<span class="font-mono text-sm">{subject.value}</span>
						{#if subject.kind_label}
							<Badge variant="secondary" class="h-5 text-[10px]">{subject.kind_label}</Badge>
						{/if}
						<span class="flex-1"></span>
						{#each offered as tool (tool.name)}
							{@const Icon = toolIcon(tool.icon)}
							{@const already = toolbox.runs.some((r) => r.tool === tool.name)}
							<span class="flex items-center gap-0.5">
								<Hint text={tool.description}>
									{#snippet child(props)}
										<span {...props} class="inline-flex">
											<Button
												variant="outline"
												size="sm"
												class="h-7 gap-1.5 px-2 text-xs"
												disabled={already}
												onclick={() => addTool(tool.name)}
											>
												{#if already}
													<Icon class="size-3" />
												{:else}
													<Plus class="size-3" />
												{/if}
												{tool.title}
											</Button>
										</span>
									{/snippet}
								</Hint>
								<ToolOptions
									{tool}
									values={options[tool.name] ?? {}}
									onChange={(k, v) => setOption(tool.name, k, v)}
								/>
							</span>
						{/each}
					</div>

					{#each toolbox.runs as run (run.id)}
						<RunSection {run} onLookup={chase} onNavigate={() => (open = false)} />
					{/each}
				{:else if !toolbox.busy}
					<div class="space-y-5 py-2">
						{#if recent.length}
							<div>
								<div class="flex items-baseline justify-between pb-1.5">
									<h4 class="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
										Recent
									</h4>
									<Button
										variant="ghost"
										size="sm"
										class="h-6 px-2 text-xs"
										onclick={() => toolbox.clear()}>Clear</Button
									>
								</div>
								{#each recent as run (run.id)}
									{@const Icon = toolIcon(toolbox.tool(run.tool)?.icon ?? '')}
									<button
										type="button"
										onclick={() => replay(run)}
										class="flex w-full items-center gap-2.5 rounded-md border-b border-border/40 px-1 py-2 text-left last:border-0 hover:bg-accent/40"
									>
										<Icon class="size-3.5 shrink-0 text-muted-foreground" />
										<span class="min-w-0 flex-1">
											<span class="block truncate font-mono text-xs">{run.label}</span>
											<span class="block truncate text-[11px] text-muted-foreground">
												{run.title} · {run.status === 'failed'
													? 'failed'
													: (run.summary ?? run.status)}
											</span>
										</span>
										<span class="shrink-0 text-[11px] text-muted-foreground">
											{relativeTime(run.finished_at ?? run.queued_at)}
										</span>
									</button>
								{/each}
							</div>
						{/if}

						{#if examples.length}
							<div class="flex flex-wrap items-center gap-1.5">
								<span class="text-[11px] text-muted-foreground">Examples</span>
								{#each examples as example (example)}
									<Button
										variant="outline"
										size="sm"
										class="h-6 px-2 font-mono text-[11px]"
										onclick={() => submit(example)}
									>
										{example}
									</Button>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</ScrollArea>
	</Dialog.Content>
</Dialog.Root>
