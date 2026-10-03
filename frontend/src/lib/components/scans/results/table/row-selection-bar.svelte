<script lang="ts">
	import type { Snippet } from 'svelte';
	import Copy from '@lucide/svelte/icons/copy';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import ExportMenu from '../export-menu.svelte';
	import { surfaceApi } from '$lib/api/surface';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { SURFACE, type SurfaceDimension } from '$lib/config/surface';
	import type { SurfaceDeleteResult } from '$lib/types/surface';

	interface CopyOption {
		label: string;
		values: () => string[];
	}

	interface HideOption {
		label: string;
		tokens: () => string[];
	}

	interface Props {
		count: number;
		dimension: SurfaceDimension;
		projectId: string;
		scanId?: string;
		noun?: string;
		nounPlural?: string;
		removes?: string;
		copy: CopyOption[];
		hide?: HideOption[];
		onHide?: (tokens: string[]) => void;
		ids: () => string[];
		deleteKey?: string;
		exportIds?: () => string[];
		exportFilters?: Record<string, unknown>;
		onDeleted?: (result: SurfaceDeleteResult) => void;
		onClear: () => void;
		actions?: Snippet;
	}

	let {
		count,
		dimension,
		projectId,
		scanId = '',
		noun,
		nounPlural,
		removes,
		copy,
		hide = [],
		onHide,
		ids,
		deleteKey,
		exportIds,
		exportFilters = {},
		onDeleted,
		onClear,
		actions
	}: Props = $props();

	const spec = $derived(SURFACE[dimension]);
	const one = $derived(noun ?? spec.noun);
	const many = $derived(nounPlural ?? spec.nounPlural);
	const label = $derived(count === 1 ? one : many);
	const goes = $derived(removes ?? spec.children);

	let confirming = $state(false);
	let removing = $state(false);
	let doomed = $state<string[]>([]);

	const body = $derived(
		goes
			? `${count.toLocaleString()} ${label} and ${count === 1 ? 'its' : 'their'} ${goes} are removed.`
			: `${count.toLocaleString()} ${label} ${count === 1 ? 'is' : 'are'} removed.`
	);

	async function copyValues(option: CopyOption) {
		const values = option.values();
		if (!values.length) return;
		if (await writeClipboard(values.join('\n')))
			toast.success(`${values.length.toLocaleString()} ${option.label} copied`);
		else toast.error(`${option.label.charAt(0).toUpperCase()}${option.label.slice(1)} not copied`);
	}

	function hideValues(option: HideOption) {
		const tokens = option.tokens();
		if (!tokens.length) return;
		onHide?.(tokens);
	}

	function openConfirm() {
		doomed = ids();
		confirming = true;
	}

	async function remove() {
		removing = true;
		try {
			const result = await surfaceApi.remove(
				{ dimension, ids: doomed, key: deleteKey ?? null },
				{ projectId, scanId }
			);
			confirming = false;
			toast.success(
				`${result.deleted.toLocaleString()} ${result.deleted === 1 ? spec.noun : spec.nounPlural} deleted`
			);
			onDeleted?.(result);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${spec.label} not deleted`);
		} finally {
			removing = false;
		}
	}
</script>

<SelectionActionBar selectedCount={count} noun={one} nounPlural={many} {onClear}>
	{#if actions}{@render actions()}{/if}

	{#if copy.length === 1}
		<Button variant="ghost" size="sm" onclick={() => copyValues(copy[0])}>
			<Copy class="h-3.5 w-3.5 text-muted-foreground" />
			Copy {copy[0].label}
		</Button>
	{:else if copy.length > 1}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="ghost" size="sm">
						<Copy class="h-3.5 w-3.5 text-muted-foreground" />
						Copy
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="w-44">
				{#each copy as option (option.label)}
					<DropdownMenu.Item onclick={() => copyValues(option)}>
						Copy {option.label}
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	{/if}

	{#if onHide && hide.length === 1}
		<Button variant="ghost" size="sm" onclick={() => hideValues(hide[0])}>
			<EyeOff class="h-3.5 w-3.5 text-muted-foreground" />
			Hide all {hide[0].label}
		</Button>
	{:else if onHide && hide.length > 1}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="ghost" size="sm">
						<EyeOff class="h-3.5 w-3.5 text-muted-foreground" />
						Hide
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="w-64">
				{#each hide as option (option.label)}
					<DropdownMenu.Item onclick={() => hideValues(option)}>
						<span class="truncate">Hide all {option.label}</span>
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	{/if}

	<ExportMenu
		{dimension}
		{projectId}
		{scanId}
		filters={exportFilters}
		ids={(exportIds ?? ids)()}
		compact
	/>

	<Button
		variant="ghost"
		size="sm"
		class="text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={openConfirm}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>

<ConfirmDialog
	bind:open={confirming}
	title="Delete {count.toLocaleString()} {label}"
	description={body}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	destructive
	loading={removing}
	onOpenChange={(value) => (confirming = value)}
	onConfirm={remove}
/>
