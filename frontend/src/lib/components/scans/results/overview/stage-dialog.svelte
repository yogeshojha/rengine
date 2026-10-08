<script lang="ts">
	import { untrack } from 'svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Circle from '@lucide/svelte/icons/circle';
	import SquareTerminal from '@lucide/svelte/icons/square-terminal';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CodeBlock from '$lib/components/code-block.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { scansApi } from '$lib/api/scans';
	import {
		activityStatusIcon,
		activityStatusClass,
		ACTIVITY_STATUS_LABEL
	} from '$lib/utilities/scan-status';
	import { formatSeconds } from '$lib/utilities/format';
	import type { BadgeVariant } from '$lib/components/ui/badge';
	import type {
		ScanActivityRead,
		ScanActivityStatus,
		ScanCommandDetail,
		ScanCommandRead
	} from '$lib/types/scan';
	import { formatClock } from '$lib/utilities/dates';

	interface Props {
		open: boolean;
		title: string;
		description: string;
		activity: ScanActivityRead | null;
		scanId: string;
		projectId: string;
	}

	let {
		open = $bindable(false),
		title,
		description,
		activity,
		scanId,
		projectId
	}: Props = $props();

	const STATUS_VARIANT: Record<ScanActivityStatus, BadgeVariant> = {
		pending: 'secondary',
		running: 'info',
		paused: 'secondary',
		success: 'success',
		partial: 'warning',
		failed: 'destructive',
		skipped: 'outline',
		aborted: 'warning'
	};

	let outputs = $state<Record<string, string | null>>({});
	let loadingId = $state<string | null>(null);
	let commands = $state<ScanCommandRead[] | null>(null);
	let commandsFailed = $state(false);
	let commandsFor: string | null = null;

	$effect(() => {
		const id = activity?.id;
		void activity?.status;
		if (!open || !id) return;
		untrack(() => loadCommands(id));
	});

	async function loadCommands(id: string) {
		if (commandsFor !== id) {
			commandsFor = id;
			commands = null;
			commandsFailed = false;
		}
		try {
			const rows = await scansApi.commands(scanId, projectId, id);
			if (commandsFor === id) commands = rows;
		} catch {
			if (commandsFor === id) commandsFailed = true;
		}
	}

	$effect(() => {
		void activity?.id;
		outputs = {};
	});

	async function loadOutput(id: string) {
		if (id in outputs || loadingId === id) return;
		loadingId = id;
		try {
			const detail: ScanCommandDetail = await scansApi.command(scanId, id, projectId);
			outputs[id] = detail.output ?? '';
		} catch {
			outputs[id] = null;
		} finally {
			loadingId = null;
		}
	}

	function retryCommands() {
		if (!activity) return;
		commandsFailed = false;
		void loadCommands(activity.id);
	}

	function retryOutput(id: string) {
		delete outputs[id];
		void loadOutput(id);
	}

	let Icon = $derived(activity ? activityStatusIcon(activity.status) : Circle);
	let figures = $derived(activity?.figures ?? []);
	let notes = $derived(
		Object.entries(activity?.result ?? {}).filter(
			(e): e is [string, string] => typeof e[1] === 'string'
		)
	);
	let meta = $derived.by(() => {
		if (!activity) return description;
		const parts: string[] = [];
		if (activity.started_at) parts.push(`Started ${formatClock(activity.started_at)}`);
		const dur = formatSeconds(activity.duration_seconds);
		if (dur) parts.push(dur);
		if (commands)
			parts.push(`${commands.length} ${commands.length === 1 ? 'command' : 'commands'}`);
		return parts.join(' · ');
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		class="grid max-h-[85vh] grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-2xl"
	>
		<Dialog.Header class="border-b px-6 py-4 text-left">
			<Dialog.Title class="flex items-center gap-2">
				<Icon
					class="size-4 {activity
						? activityStatusClass(activity.status)
						: 'text-muted-foreground'} {activity?.status === 'running' ? 'animate-spin' : ''}"
				/>
				{title}
				{#if activity}
					<Badge variant={STATUS_VARIANT[activity.status]} class="ml-1 h-5 font-normal">
						{ACTIVITY_STATUS_LABEL[activity.status]}
					</Badge>
				{/if}
			</Dialog.Title>
			<Dialog.Description>{meta}</Dialog.Description>
		</Dialog.Header>

		<ScrollArea class="min-h-0">
			<div class="flex flex-col gap-6 px-6 py-5">
				{#if !activity}
					<p class="text-sm text-muted-foreground">Stage has not run.</p>
				{:else}
					{#if figures.length}
						<section class="flex flex-col gap-2">
							<SectionHead title="Results" />
							<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
								{#each figures as figure (figure.key)}
									<div class="rounded-lg border px-3 py-2.5">
										<div class="text-lg leading-none font-semibold tracking-tight tabular-nums">
											{figure.value.toLocaleString()}
										</div>
										<div class="mt-1.5 text-xs text-muted-foreground">
											{figure.label}
										</div>
									</div>
								{/each}
							</div>
						</section>
					{/if}
					{#each notes as [key, value] (key)}
						<p class="text-sm text-muted-foreground">{value}</p>
					{/each}
					{#if activity.error}
						<p
							class="rounded-lg border p-3 font-mono text-xs break-words {activity.status ===
							'partial'
								? 'border-warning/40 bg-warning/5 text-warning'
								: 'border-destructive/40 bg-destructive/5 text-destructive'}"
						>
							{activity.error}
						</p>
					{/if}

					<section class="flex flex-col gap-2">
						<SectionHead title="Commands" />
						{#if !commands && commandsFailed}
							<EmptyState compact icon={TriangleAlert} title="Commands not loaded">
								<Button variant="outline" size="sm" onclick={() => retryCommands()}>Retry</Button>
							</EmptyState>
						{:else if !commands}
							<div class="flex flex-col gap-1.5">
								<Skeleton class="h-9 w-full" />
								<Skeleton class="h-9 w-full" />
							</div>
						{:else if !commands.length}
							<EmptyState compact icon={SquareTerminal} title="No commands recorded" />
						{:else}
							<div class="flex flex-col gap-1.5">
								{#each commands as c (c.id)}
									{@const CIcon = activityStatusIcon(c.status)}
									<Collapsible.Root onOpenChange={(o) => o && loadOutput(c.id)}>
										<Collapsible.Trigger
											class="group flex w-full cursor-pointer items-start gap-2 rounded-md border px-3 py-2 text-left transition-colors hover:bg-muted/40"
										>
											<span class="flex h-4 shrink-0 items-center">
												<ChevronRight
													class="size-3.5 text-muted-foreground transition-transform group-data-[state=open]:rotate-90"
												/>
											</span>
											<span class="flex h-4 shrink-0 items-center">
												<CIcon
													class="size-3.5 {activityStatusClass(c.status)} {c.status === 'running'
														? 'animate-spin'
														: ''}"
												/>
											</span>
											<span class="flex min-w-0 flex-1 flex-col gap-0.5">
												<span class="flex items-center gap-2 text-xs leading-4">
													<span class="font-mono font-medium">{c.tool}</span>
													<span
														class="ml-auto flex shrink-0 gap-2 text-muted-foreground tabular-nums"
													>
														{#if c.return_code != null}<span>rc {c.return_code}</span>{/if}
														{#if formatSeconds(c.duration_seconds)}
															<span>{formatSeconds(c.duration_seconds)}</span>
														{/if}
													</span>
												</span>
												<span class="font-mono text-xs leading-4 break-all text-muted-foreground">
													{c.command}
												</span>
												{#if c.error}
													<span class="text-xs leading-4 text-destructive">{c.error}</span>
												{/if}
											</span>
										</Collapsible.Trigger>
										<Collapsible.Content>
											<div
												class="mt-1 rounded-md border bg-muted/30"
												role="region"
												aria-label="{c.tool} output"
											>
												{#if loadingId === c.id}
													<div class="flex flex-col gap-1.5 p-3" aria-busy="true">
														{#each Array(6) as _, i (i)}
															<Skeleton
																class="h-3 {i % 3 === 0
																	? 'w-1/2'
																	: i % 3 === 1
																		? 'w-5/6'
																		: 'w-2/3'}"
															/>
														{/each}
													</div>
												{:else if outputs[c.id] === null}
													<div class="flex items-center justify-between gap-3 p-3">
														<p class="text-xs text-muted-foreground">Output not loaded.</p>
														<Button variant="outline" size="sm" onclick={() => retryOutput(c.id)}>
															Retry
														</Button>
													</div>
												{:else if outputs[c.id]}
													{@const out = outputs[c.id] ?? ''}
													<CodeBlock
														code={out}
														label="{c.tool} output"
														maxHeight="16rem"
														maxLines={0}
														class="rounded-none border-0"
													/>
												{:else}
													<p class="p-3 text-xs text-muted-foreground">No output captured.</p>
												{/if}
											</div>
										</Collapsible.Content>
									</Collapsible.Root>
								{/each}
							</div>
						{/if}
					</section>
				{/if}
			</div>
		</ScrollArea>
	</Dialog.Content>
</Dialog.Root>
