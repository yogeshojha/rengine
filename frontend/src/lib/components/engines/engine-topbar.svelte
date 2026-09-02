<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Save from '@lucide/svelte/icons/save';
	import Play from '@lucide/svelte/icons/play';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Download from '@lucide/svelte/icons/download';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Terminal from '@lucide/svelte/icons/terminal';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import LoadingButton from '@/components/loading-button.svelte';
	import type { Intensity, ScanEngine } from '$lib/types/scan-engine';
	import { INTENSITIES, INTENSITY_HELP } from '$lib/types/scan-engine';

	interface Props {
		engine: ScanEngine;
		isSaving: boolean;
		hasUnsavedChanges: boolean;
		onSave: () => void;
		onNameChange: (name: string) => void;
		onIntensityChange: (intensity: Intensity) => void;
		onToolOptions: () => void;
		onRun: () => void;
		onBack: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
		onExportYaml?: () => void;
	}

	let {
		engine,
		isSaving,
		hasUnsavedChanges,
		onSave,
		onNameChange,
		onIntensityChange,
		onToolOptions,
		onRun,
		onBack,
		onDuplicate,
		onDelete,
		onExportYaml
	}: Props = $props();

	let editingName = $state(false);
	let draftName = $state('');

	function startEdit() {
		draftName = engine.name;
		editingName = true;
	}

	function commit() {
		const next = draftName.trim();
		if (next && next !== engine.name) onNameChange(next);
		editingName = false;
	}
</script>

<div class="topbar">
	<div class="left">
		<Button variant="ghost" size="icon-sm" aria-label="Back to engines" onclick={onBack}>
			<ArrowLeft size={15} />
		</Button>
		<Separator orientation="vertical" class="data-[orientation=vertical]:h-[18px]" />

		{#if editingName}
			<!-- svelte-ignore a11y_autofocus -->
			<Input
				bind:value={draftName}
				onblur={commit}
				onkeydown={(e) => {
					if (e.key === 'Enter') commit();
					else if (e.key === 'Escape') editingName = false;
				}}
				autofocus
				class="h-7 max-w-[260px] text-sm font-semibold"
				placeholder="Engine name…"
			/>
		{:else}
			<div class="name-row">
				<span class="name">{engine.name || 'Untitled engine'}</span>
				<Button
					variant="ghost"
					size="icon-sm"
					class="h-6 w-6 text-muted-foreground"
					aria-label="Rename engine"
					onclick={startEdit}
				>
					<Pencil size={11} />
				</Button>
			</div>
		{/if}
	</div>

	<div class="center">
		<span class="intensity-label">Intensity</span>
		<Tabs.Root
			value={engine.intensity}
			onValueChange={(v) => onIntensityChange(v as Intensity)}
			class="flex-row"
		>
			<Tabs.List class="h-8">
				{#each INTENSITIES as level (level)}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<Tabs.Trigger {...props} value={level} class="px-3 text-xs capitalize">
									{level}
								</Tabs.Trigger>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content class="max-w-[220px] text-xs">{INTENSITY_HELP[level]}</Tooltip.Content>
					</Tooltip.Root>
				{/each}
			</Tabs.List>
		</Tabs.Root>
	</div>

	<div class="right">
		<Button variant="outline" size="sm" class="h-7 gap-1.5 text-xs" onclick={onRun}>
			<Play size={13} />
			Run
		</Button>

		<Button variant="outline" size="sm" class="h-7 gap-1.5 text-xs" onclick={onToolOptions}>
			<Terminal size={13} />
			Tool args
		</Button>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="icon-sm" class="h-7 w-7" aria-label="More">
						<MoreHorizontal size={14} />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-44">
				<DropdownMenu.Item disabled={!onExportYaml} onclick={() => onExportYaml?.()}>
					<Download size={13} />
					Export YAML
				</DropdownMenu.Item>
				<DropdownMenu.Item disabled={!onDuplicate} onclick={() => onDuplicate?.()}>
					<Copy size={13} />
					Duplicate
				</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Item variant="destructive" disabled={!onDelete} onclick={() => onDelete?.()}>
					<Trash2 size={13} />
					Delete
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<LoadingButton
			size="sm"
			class="h-7 gap-1.5 text-xs"
			loading={isSaving}
			loadingLabel="Saving…"
			disabled={!hasUnsavedChanges}
			onclick={onSave}
		>
			<Save size={13} />
			{hasUnsavedChanges ? 'Save changes' : 'Saved'}
		</LoadingButton>
	</div>
</div>

<style>
	.topbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		flex-wrap: wrap;
		flex-shrink: 0;
		height: auto;
		min-height: 52px;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border);
		background: var(--card);
	}

	.left,
	.center,
	.right {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}

	.name-row {
		display: flex;
		align-items: center;
		gap: 2px;
		min-width: 0;
	}
	.name {
		font-size: 14px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.intensity-label {
		font-size: 11px;
		color: var(--muted-foreground);
	}

	@media (max-width: 900px) {
		.center {
			order: 3;
			width: 100%;
		}
	}
</style>
