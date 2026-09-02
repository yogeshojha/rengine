<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ButtonGroup from '$lib/components/ui/button-group';
	import * as Kbd from '$lib/components/ui/kbd';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Save from '@lucide/svelte/icons/save';
	import Check from '@lucide/svelte/icons/check';
	import Play from '@lucide/svelte/icons/play';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Download from '@lucide/svelte/icons/download';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Terminal from '@lucide/svelte/icons/terminal';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import LoadingButton from '@/components/loading-button.svelte';
	import type { Intensity, ScanEngine } from '$lib/types/scan-engine';
	import { INTENSITIES, INTENSITY_HELP, INTENSITY_LABELS } from '$lib/types/scan-engine';

	interface Props {
		engine: ScanEngine;
		isSaving: boolean;
		hasUnsavedChanges: boolean;
		errorCount: number;
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
		errorCount,
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

	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

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

<header class="topbar">
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
				class="h-7 max-w-[280px] text-sm font-semibold"
				placeholder="Engine name…"
			/>
		{:else}
			<button type="button" class="name-btn" onclick={startEdit} aria-label="Rename engine">
				<span class="name">{engine.name || 'Untitled engine'}</span>
				<Pencil size={11} class="pencil" />
			</button>
		{/if}

		{#if hasUnsavedChanges}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<span {...props} class="dot" aria-label="Unsaved changes"></span>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="text-xs">Unsaved changes</Tooltip.Content>
			</Tooltip.Root>
		{/if}
	</div>

	<div class="center">
		<ToggleGroup.Root
			type="single"
			variant="outline"
			size="sm"
			value={engine.intensity}
			onValueChange={(v) => v && onIntensityChange(v as Intensity)}
			aria-label="Intensity"
		>
			{#each INTENSITIES as level (level)}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<ToggleGroup.Item
								{...props}
								value={level}
								class="h-7 px-3 text-xs data-[state=on]:bg-foreground data-[state=on]:text-background dark:data-[state=on]:bg-foreground dark:data-[state=on]:text-background"
							>
								{INTENSITY_LABELS[level]}
							</ToggleGroup.Item>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="max-w-[220px] text-xs">{INTENSITY_HELP[level]}</Tooltip.Content>
				</Tooltip.Root>
			{/each}
		</ToggleGroup.Root>
	</div>

	<div class="right">
		<Button variant="ghost" size="sm" class="h-7 gap-1.5 px-2 text-xs" onclick={onToolOptions}>
			<Terminal size={13} />
			Tool args
		</Button>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="ghost" size="icon-sm" class="h-7 w-7" aria-label="More">
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

		<ButtonGroup.Root>
			<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onRun}>
				<Play size={13} />
				Run
			</Button>
			<LoadingButton
				size="sm"
				variant={hasUnsavedChanges ? 'default' : 'outline'}
				class="h-8 gap-1.5 text-xs"
				loading={isSaving}
				loadingLabel="Saving…"
				disabled={!hasUnsavedChanges || errorCount > 0}
				onclick={onSave}
			>
				{#if hasUnsavedChanges}
					<Save size={13} />
					Save
					<Kbd.Group class="ml-0.5 hidden sm:inline-flex">
						<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">
							{isMac ? '⌘' : 'Ctrl'}
						</Kbd.Root>
						<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">S</Kbd.Root>
					</Kbd.Group>
				{:else}
					<Check size={13} />
					Saved
				{/if}
			</LoadingButton>
		</ButtonGroup.Root>
	</div>
</header>

<style>
	.topbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px 16px;
		flex-wrap: wrap;
		flex-shrink: 0;
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
	.left {
		flex: 1 1 auto;
	}

	.name-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		padding: 2px 6px;
		margin-left: -6px;
		border-radius: 6px;
		background: none;
		border: none;
		color: inherit;
		cursor: text;
	}
	.name-btn:hover {
		background: var(--muted);
	}
	.name-btn :global(.pencil) {
		flex-shrink: 0;
		color: var(--muted-foreground);
		opacity: 0;
		transition: opacity 0.12s ease;
	}
	.name-btn:hover :global(.pencil),
	.name-btn:focus-visible :global(.pencil) {
		opacity: 1;
	}
	.name {
		font-size: 14px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.dot {
		display: inline-block;
		width: 7px;
		height: 7px;
		border-radius: 999px;
		background: var(--primary);
		flex-shrink: 0;
	}

	@media (max-width: 900px) {
		.center {
			order: 3;
			width: 100%;
		}
	}
</style>
