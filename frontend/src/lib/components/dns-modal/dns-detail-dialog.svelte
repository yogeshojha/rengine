<script lang="ts">
	import Network from '@lucide/svelte/icons/network';
	import { targetsApi } from '$lib/api/targets';
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import DnsTab from '$lib/components/targets/target-detail/dns/dns-tab.svelte';
	import RelatedTargets from '$lib/components/targets/related-targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { TargetRelation } from '$lib/config/relations';
	import { TaskStatus } from '$lib/types/task-status';
	import type { DnsLookupRead } from '$lib/types/target-detail';
	import type { RelatedTarget } from '$lib/types/relations';
	import { toast } from 'svelte-sonner';

	interface Props {
		open: boolean;
		targetId?: string | null;
		targetValue?: string | null;
		onOpenChange: (open: boolean) => void;
	}

	let { open, targetId = null, targetValue = null, onOpenChange }: Props = $props();

	const KINDS = [TargetRelation.DNS_RECORD, TargetRelation.NAMESERVER];
	const POLL_MS = 2500;
	const MAX_POLLS = 30;

	let lookup = $state<DnsLookupRead | null>(null);
	let status = $state<TaskStatus>(TaskStatus.PENDING);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let refreshing = $state(false);
	let relations = $state<RelatedTarget[]>([]);
	let loadedFor: string | null = null;
	let pollTimer: ReturnType<typeof setTimeout> | null = null;

	const isPending = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;

	function stopPolling() {
		if (pollTimer) clearTimeout(pollTimer);
		pollTimer = null;
	}

	function poll(id: string, attempt = 1) {
		stopPolling();
		pollTimer = setTimeout(async () => {
			await load(id, true);
			if (open && targetId === id && isPending(status) && attempt < MAX_POLLS) {
				poll(id, attempt + 1);
			}
		}, POLL_MS);
	}

	async function load(id: string, silent = false) {
		if (!silent) loading = true;
		try {
			const res = await targetsApi.getDns(id);
			lookup = res.lookup;
			status = res.status;
			error = res.error;
		} catch {
			lookup = null;
			status = TaskStatus.FAILED;
			error = 'DNS records not loaded';
			loadedFor = null;
		} finally {
			loading = false;
		}
	}

	async function loadRelations(id: string) {
		const project = projectsStore.activeProject;
		if (!project) return;
		try {
			relations = (await targetsApi.getRelations(id, project.id)).items;
		} catch {
			relations = [];
		}
	}

	async function refresh() {
		if (!targetId) return;
		refreshing = true;
		try {
			await targetsApi.refreshDns(targetId);
			toast.success('DNS refresh started');
			status = TaskStatus.PENDING;
			poll(targetId);
		} catch {
			toast.error('DNS not refreshed');
		} finally {
			refreshing = false;
		}
	}

	$effect(() => {
		if (!open) {
			loadedFor = null;
			stopPolling();
			return;
		}
		if (!targetId || loadedFor === targetId) return;
		loadedFor = targetId;
		void load(targetId);
		void loadRelations(targetId);
	});

	$effect(() => stopPolling);
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b px-6 py-4 pr-12">
			<div class="flex items-center gap-3">
				<div
					class="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-muted/40"
				>
					<Network class="size-5 text-muted-foreground" />
				</div>
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<Dialog.Title class="truncate font-mono">{targetValue ?? 'DNS records'}</Dialog.Title>
					<Dialog.Description>DNS records</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<ScrollArea class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-5rem)]">
			<div class="flex flex-col gap-5 px-6 py-5">
				<DnsTab
					host={targetValue ?? ''}
					{lookup}
					{status}
					{error}
					{loading}
					{refreshing}
					ipsScanId={null}
					onRefresh={refresh}
				/>
				<RelatedTargets {relations} kinds={KINDS} />
			</div>
		</ScrollArea>
	</Dialog.Content>
</Dialog.Root>
