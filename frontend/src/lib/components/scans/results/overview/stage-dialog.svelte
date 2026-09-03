<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Circle from '@lucide/svelte/icons/circle';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { scansApi } from '$lib/api/scans';
	import {
		activityStatusIcon,
		activityStatusClass,
		ACTIVITY_STATUS_LABEL,
		durationText
	} from '$lib/utilities/scan-status';
	import type { BadgeVariant } from '$lib/components/ui/badge';
	import type {
		ScanActivityRead,
		ScanActivityStatus,
		ScanCommandDetail,
		ScanCommandRead
	} from '$lib/types/scan';

	interface Props {
		open: boolean;
		title: string;
		description: string;
		activity: ScanActivityRead | null;
		commands: ScanCommandRead[];
		scanId: string;
		projectId: string;
	}

	let {
		open = $bindable(false),
		title,
		description,
		activity,
		commands,
		scanId,
		projectId
	}: Props = $props();

	const HIDDEN_RESULT_KEYS = new Set(['excluded']);
	const STATUS_VARIANT: Record<ScanActivityStatus, BadgeVariant> = {
		pending: 'secondary',
		running: 'info',
		success: 'success',
		failed: 'destructive',
		skipped: 'outline',
		aborted: 'warning'
	};
	const fmtTime = (iso: string) =>
		new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

	let outputs = $state<Record<string, string | null>>({});
	let loadingId = $state<string | null>(null);

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

	let Icon = $derived(activity ? activityStatusIcon(activity.status) : Circle);
	let numbers = $derived(
		Object.entries(activity?.result ?? {}).filter(
			(e): e is [string, number] => typeof e[1] === 'number' && !HIDDEN_RESULT_KEYS.has(e[0])
		)
	);
	let notes = $derived(
		Object.entries(activity?.result ?? {}).filter(
			(e): e is [string, string] => typeof e[1] === 'string'
		)
	);
	let meta = $derived.by(() => {
		if (!activity) return description;
		const parts: string[] = [];
		if (activity.started_at) parts.push(`Started ${fmtTime(activity.started_at)}`);
		const dur = durationText(activity.duration_seconds);
		if (dur) parts.push(dur);
		parts.push(`${commands.length} ${commands.length === 1 ? 'command' : 'commands'}`);
		return parts.join(' · ');
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		class="grid max-h-[85vh] grid-rows-[auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-2xl"
	>
		<Dialog.Header class="border-b px-6 py-5 text-left">
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
					<p class="text-sm text-muted-foreground">This stage has not run.</p>
				{:else}
					{#if numbers.length}
						<section>
							<h3 class="mb-2 text-xs font-medium text-muted-foreground">Results</h3>
							<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
								{#each numbers as [key, value] (key)}
									<div class="rounded-md border px-3 py-2.5">
										<div class="text-lg leading-none font-semibold tracking-tight">
											{value.toLocaleString()}
										</div>
										<div class="mt-1.5 truncate text-xs text-muted-foreground">
											{key.replace(/_/g, ' ')}
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
							class="rounded-md border border-destructive/40 bg-destructive/5 p-3 font-mono text-xs break-words text-destructive"
						>
							{activity.error}
						</p>
					{/if}

					<section>
						<h3 class="mb-2 text-xs font-medium text-muted-foreground">Commands</h3>
						{#if !commands.length}
							<p class="text-sm text-muted-foreground">No commands were recorded for this stage.</p>
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
														{#if durationText(c.duration_seconds, true)}
															<span>{durationText(c.duration_seconds, true)}</span>
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
													<p class="p-3 text-xs text-muted-foreground">Loading output…</p>
												{:else if outputs[c.id] === null}
													<p class="p-3 text-xs text-destructive">Output could not be loaded.</p>
												{:else if outputs[c.id]}
													<ScrollArea class="h-64">
														<pre
															class="p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap">{outputs[
																c.id
															]}</pre>
													</ScrollArea>
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
