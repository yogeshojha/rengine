<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Plus, RefreshCw, Radar } from 'lucide-svelte';

	import { scansStore } from '$lib/stores/scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import * as Table from '$lib/components/ui/table';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import { formatDistanceToNow } from '$lib/utilities/dates';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';

	let showLaunch = $state(false);
	let isRefreshing = $state(false);

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (!scansStore.hasFetched) {
					scansStore.fetchScans(project.id);
				}
			});
		}
	});

	const STATUS_LABEL: Record<ScanStatus, string> = {
		pending: 'Queued',
		running: 'Running',
		completed: 'Completed',
		failed: 'Failed',
		cancelled: 'Cancelled'
	};

	function statusVariant(status: ScanStatus): 'default' | 'secondary' | 'outline' | 'destructive' {
		if (status === 'failed' || status === 'cancelled') return 'destructive';
		if (status === 'completed') return 'default';
		return 'secondary';
	}

	function results(scan: ScanRead): string {
		return [
			`${scan.subdomains_found} subs`,
			`${scan.ips_found} IPs`,
			`${scan.open_ports_found} ports`,
			`${scan.vulnerabilities_found} vulns`,
			`${scan.endpoints_found} endpoints`
		].join(' · ');
	}

	async function handleRefresh() {
		const project = projectsStore.activeProject;
		if (!project) return;
		isRefreshing = true;
		try {
			await scansStore.fetchScans(project.id);
			if (scansStore.error) toast.error(scansStore.error);
		} finally {
			isRefreshing = false;
		}
	}

	function handleNewScan() {
		if (!projectsStore.activeProject) {
			toast.error('No active project selected');
			return;
		}
		showLaunch = true;
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Scans</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Launch records pairing an engine with an optional context and a target
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				aria-label="Refresh scans"
				onclick={handleRefresh}
				disabled={isRefreshing}
			>
				<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
			</Button>
			<Button onclick={handleNewScan} class="gap-2">
				<Plus class="h-4 w-4" />
				New Scan
			</Button>
		</div>
	</div>

	{#if scansStore.error && !scansStore.isLoading}
		<div
			class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
		>
			{scansStore.error}
		</div>
	{/if}

	{#if scansStore.isLoading}
		<div class="space-y-2">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-14 rounded-lg" />
			{/each}
		</div>
	{:else if scansStore.scans.length === 0}
		<Empty.Root class="border bg-muted/20 py-20">
			<Empty.Header>
				<Empty.Media class="size-16 rounded-2xl bg-muted">
					<Radar size={28} class="text-muted-foreground" />
				</Empty.Media>
				<Empty.Title class="text-lg font-bold">No scans yet</Empty.Title>
				<Empty.Description class="max-w-md">
					Launching records the resolved scan config and queues it. Scan execution dispatch is not
					wired up yet — scans stay in "Queued" until a scanner is connected.
				</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button onclick={handleNewScan} class="gap-2">
					<Plus size={15} />
					Launch Your First Scan
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<div class="rounded-lg border border-border">
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Target</Table.Head>
						<Table.Head>Engine</Table.Head>
						<Table.Head>Context</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head>Results</Table.Head>
						<Table.Head class="text-right">Created</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each scansStore.scans as scan (scan.id)}
						<Table.Row>
							<Table.Cell class="font-mono text-xs">
								{scan.execution_config.target_value}
							</Table.Cell>
							<Table.Cell>{scan.engine_name}</Table.Cell>
							<Table.Cell class="text-muted-foreground">
								{scan.context_name ?? 'engine defaults'}
							</Table.Cell>
							<Table.Cell>
								<Badge variant={statusVariant(scan.status)} class="font-normal">
									{STATUS_LABEL[scan.status] ?? scan.status}
								</Badge>
							</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{results(scan)}</Table.Cell>
							<Table.Cell class="text-right text-xs text-muted-foreground">
								{@const rel = formatDistanceToNow(scan.created_at)}
								{rel === 'just now' ? rel : `${rel} ago`}
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>

		<p class="pt-2 text-center text-xs text-muted-foreground">
			{scansStore.scans.length} scan{scansStore.scans.length !== 1 ? 's' : ''} in this project
		</p>
	{/if}
</div>

<LaunchModal bind:open={showLaunch} onClose={() => (showLaunch = false)} />
