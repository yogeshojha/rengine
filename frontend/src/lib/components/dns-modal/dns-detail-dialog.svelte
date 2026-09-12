<script lang="ts">
	import Network from '@lucide/svelte/icons/network';
	import { targetsApi } from '$lib/api/targets';
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
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

	let { open = $bindable(), targetId = null, targetValue = null, onOpenChange }: Props = $props();

	const KINDS = [TargetRelation.DNS_RECORD, TargetRelation.NAMESERVER];

	let lookup = $state<DnsLookupRead | null>(null);
	let status = $state<TaskStatus>(TaskStatus.PENDING);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let refreshing = $state(false);
	let relations = $state<RelatedTarget[]>([]);
	let loadedFor: string | null = null;

	async function load(id: string) {
		loading = true;
		try {
			const res = await targetsApi.getDns(id);
			lookup = res.lookup;
			status = res.status;
			error = res.error;
		} catch {
			lookup = null;
			error = 'DNS records not loaded';
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
		} catch {
			toast.error('DNS not refreshed');
		} finally {
			refreshing = false;
		}
	}

	$effect(() => {
		if (!open || !targetId || loadedFor === targetId) return;
		loadedFor = targetId;
		void load(targetId);
		void loadRelations(targetId);
	});
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="shrink-0 px-6 pt-6 pb-4">
			<div class="flex items-center gap-3">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
					{#if loading}
						<Spinner class="h-5 w-5 text-primary" />
					{:else}
						<Network class="h-5 w-5 text-primary" />
					{/if}
				</div>
				<div class="min-w-0 flex-1">
					<Dialog.Title class="truncate text-lg font-semibold">
						{targetValue ?? 'DNS records'}
					</Dialog.Title>
					<Dialog.Description class="text-sm text-muted-foreground">DNS records</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-5 px-6 pb-6">
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
