<script lang="ts">
	import Download from '@lucide/svelte/icons/download';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { isLive } from '$lib/config/exports';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import ExportMenuItems from './export-menu-items.svelte';
	import ExportsSheet from './exports-sheet.svelte';

	interface Props {
		dimension: string;
		projectId: string;
		scanId?: string;
		targetId?: string;
		filters: Record<string, unknown>;
		ids?: string[];
		compact?: boolean;
	}

	let {
		dimension,
		projectId,
		scanId = '',
		targetId = '',
		filters,
		ids = [],
		compact = false
	}: Props = $props();

	let sheetOpen = $state(false);
	let pending = $state(false);
	let withEvidence = $state(false);
	let live = $derived(exportsStore.rows.some((row) => isLive(row.status)));
</script>

<DropdownMenu.Root>
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props: tip })}
				<DropdownMenu.Trigger {...tip}>
					{#snippet child({ props })}
						<Button
							{...props}
							variant={compact ? 'ghost' : 'outline'}
							size={compact ? 'sm' : 'default'}
							disabled={!projectId}
							aria-label="Export"
						>
							{#if pending || live}
								<Spinner class={compact ? 'size-3.5' : 'size-4'} />
							{:else}
								<Download class={compact ? 'size-3.5 text-muted-foreground' : 'size-4'} />
							{/if}
							<span class={compact ? '' : 'hidden 2xl:inline'}>Export</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content class={compact ? 'hidden' : '2xl:hidden'}>Export</Tooltip.Content>
	</Tooltip.Root>
	<DropdownMenu.Content align={compact ? 'center' : 'end'} class="w-48">
		<DropdownMenu.Label>{compact ? 'Export selection' : 'Export this view'}</DropdownMenu.Label>
		<DropdownMenu.Separator />
		<ExportMenuItems
			{dimension}
			{projectId}
			{scanId}
			{targetId}
			{filters}
			{ids}
			onHistory={compact ? undefined : () => (sheetOpen = true)}
			onPending={(value) => (pending = value)}
			bind:withEvidence
		/>
	</DropdownMenu.Content>
</DropdownMenu.Root>

{#if !compact}
	<ExportsSheet bind:open={sheetOpen} {projectId} {scanId} {targetId} />
{/if}
