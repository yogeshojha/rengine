<script lang="ts">
	import RadioTower from '@lucide/svelte/icons/radio-tower';
	import Radio from '@lucide/svelte/icons/radio';
	import { targetsApi } from '$lib/api/targets';
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import BgpTab from '$lib/components/targets/target-detail/bgp/bgp-tab.svelte';
	import RelatedTargets from '$lib/components/targets/related-targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { TargetRelation } from '$lib/config/relations';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetBgpDetailResponse } from '$lib/types/target-detail';
	import type { RelatedTarget } from '$lib/types/relations';
	import { toast } from 'svelte-sonner';

	interface Props {
		open: boolean;
		targetId?: string | null;
		targetValue?: string | null;
		targetType?: TargetType | null;
		onOpenChange: (open: boolean) => void;
		onAddAsTarget?: (value: string) => void;
	}

	let {
		open = $bindable(),
		targetId = null,
		targetValue = null,
		targetType = null,
		onOpenChange,
		onAddAsTarget
	}: Props = $props();

	const NETWORK_KINDS = [TargetRelation.NETWORK, TargetRelation.NETWORK_CIDR];
	const POLL_MS = 2500;
	const MAX_POLLS = 30;

	let bgp = $state<TargetBgpDetailResponse | null>(null);
	let status = $state<TaskStatus>(TaskStatus.PENDING);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let refreshing = $state(false);
	let relations = $state<RelatedTarget[]>([]);
	let loadedFor: string | null = null;
	let pollTimer: ReturnType<typeof setTimeout> | null = null;

	let DialogIcon = $derived(targetType === TargetType.ASN ? RadioTower : Radio);

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
			bgp = await targetsApi.getBgp(id);
			status = bgp.status;
			error = null;
		} catch {
			bgp = null;
			status = TaskStatus.FAILED;
			error = 'BGP data not loaded';
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
			await targetsApi.refreshBgp(targetId);
			toast.success('BGP refresh started');
			status = TaskStatus.PENDING;
			error = null;
			poll(targetId);
		} catch {
			toast.error('BGP not refreshed');
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
		bgp = null;
		relations = [];
		void load(targetId);
		void loadRelations(targetId);
	});

	$effect(() => stopPolling);
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="shrink-0 px-6 pt-6 pb-4">
			<div class="flex items-center gap-3">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
					{#if loading}
						<Spinner class="h-5 w-5 text-primary" />
					{:else}
						<DialogIcon class="h-5 w-5 text-primary" />
					{/if}
				</div>
				<div class="min-w-0 flex-1">
					<Dialog.Title class="truncate font-mono text-lg font-semibold">
						{targetValue ?? 'BGP routing'}
					</Dialog.Title>
					<Dialog.Description class="text-sm text-muted-foreground">BGP routing</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-5 px-6 pb-6">
				<BgpTab
					targetValue={targetValue ?? ''}
					targetType={targetType ?? TargetType.IP}
					{bgp}
					{status}
					{error}
					{loading}
					{refreshing}
					onRefresh={refresh}
					{onAddAsTarget}
				/>
				<RelatedTargets {relations} kinds={NETWORK_KINDS} />
			</div>
		</ScrollArea>
	</Dialog.Content>
</Dialog.Root>
