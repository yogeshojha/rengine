<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tabs from '$lib/components/ui/tabs';
	import { ArrowLeft, Save, Copy, Trash2, Download, LayoutGrid, Code2, Loader2, Pencil, Play, Plus } from 'lucide-svelte';
	import type { ScanEngine, Intensity } from '$lib/types/engine';

	interface Props {
		engine: ScanEngine | null;
		isSaving: boolean;
		viewMode: 'canvas' | 'yaml';
		previewMode?: boolean;
		toolCount?: number;
		estDuration?: string;
		hasUnsavedChanges?: boolean;
		onSave?: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
		onExportYaml?: () => void;
		onViewModeChange?: (mode: 'canvas' | 'yaml') => void;
		onNameChange?: (name: string) => void;
		onIntensityChange?: (intensity: Intensity) => void;
		onTogglePreview?: () => void;
		onAddStep?: () => void;
		onBack?: () => void;
	}

	let {
		engine,
		isSaving,
		viewMode,
		previewMode = false,
		toolCount,
		estDuration,
		hasUnsavedChanges = false,
		onSave,
		onDuplicate,
		onDelete,
		onExportYaml,
		onViewModeChange,
		onNameChange,
		onIntensityChange,
		onTogglePreview,
		onAddStep,
		onBack
	}: Props = $props();

	let isEditingName = $state(false);
	let editNameValue = $state('');

	function startEditName() {
		editNameValue = engine?.name ?? '';
		isEditingName = true;
	}

	function commitName() {
		const next = editNameValue.trim();
		if (next && next !== engine?.name) {
			onNameChange?.(next);
		}
		isEditingName = false;
	}

	function handleNameKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter') commitName();
		else if (e.key === 'Escape') isEditingName = false;
	}
</script>

<div class="topbar">
	<!-- Left: back + name -->
	<div class="topbar-left">
		<Button variant="ghost" size="icon-sm" onclick={() => onBack?.()}>
			<ArrowLeft size={15} />
		</Button>

		<Separator orientation="vertical" class="data-[orientation=vertical]:h-[18px]" />

		{#if isEditingName}
			<Input
				value={editNameValue}
				oninput={(e) => (editNameValue = e.currentTarget.value)}
				onblur={commitName}
				onkeydown={handleNameKeyDown}
				autofocus
				class="h-7 text-sm font-semibold max-w-[240px]"
				placeholder="Engine name…"
			/>
		{:else}
			<div class="name-row">
				<span class="engine-name">{engine?.name ?? 'Untitled Engine'}</span>
				<Button variant="ghost" size="icon-sm" class="h-6 w-6 text-muted-foreground" onclick={startEditName}>
					<Pencil size={11} />
				</Button>
			</div>
		{/if}

		{#if toolCount !== undefined}
			<Badge
				variant="secondary"
				class="gap-1 rounded-[5px] border border-border bg-muted font-normal text-[11px]"
			>
				<span class="font-semibold text-foreground">{toolCount} tools</span>
				{#if estDuration}
					<span class="opacity-50">·</span>
					<span>~{estDuration}</span>
				{/if}
			</Badge>
		{/if}
	</div>

	<!-- Center: intensity -->
	<Tabs.Root
		value={engine?.intensity}
		onValueChange={(v) => onIntensityChange?.(v as Intensity)}
		class="flex-row"
	>
		<Tabs.List class="h-8">
			<Tabs.Trigger value="passive" class="text-xs px-3">Passive</Tabs.Trigger>
			<Tabs.Trigger value="normal" class="text-xs px-3">Normal</Tabs.Trigger>
			<Tabs.Trigger value="aggressive" class="text-xs px-3">Aggressive</Tabs.Trigger>
		</Tabs.List>
	</Tabs.Root>

	<!-- Right: view toggle + actions -->
	<div class="topbar-right">
		<Tabs.Root
			value={viewMode}
			onValueChange={(v) => onViewModeChange?.(v as 'canvas' | 'yaml')}
			class="flex-row"
		>
			<Tabs.List class="h-8">
				<Tabs.Trigger value="canvas" class="text-xs px-3 gap-1.5">
					<LayoutGrid size={13} />
					Canvas
				</Tabs.Trigger>
				<Tabs.Trigger value="yaml" class="text-xs px-3 gap-1.5">
					<Code2 size={13} />
					YAML
				</Tabs.Trigger>
			</Tabs.List>
		</Tabs.Root>

		<Separator orientation="vertical" class="data-[orientation=vertical]:h-[18px]" />

		<Button variant="outline" size="sm" onclick={() => onAddStep?.()} class="gap-1.5 h-7 text-xs">
			<Plus size={14} />
			Add Step
		</Button>

		<Button
			variant={previewMode ? 'default' : 'outline'}
			size="sm"
			onclick={() => onTogglePreview?.()}
			class="gap-1.5 h-7 text-xs"
		>
			<Play size={14} />
			{previewMode ? 'Exit Preview' : 'Preview Run'}
		</Button>

		<Separator orientation="vertical" class="data-[orientation=vertical]:h-[18px]" />

		<Button variant="outline" size="sm" onclick={() => onExportYaml?.()} class="gap-1.5 h-7 text-xs">
			<Download size={13} />
			Export
		</Button>

		<Button variant="outline" size="sm" onclick={() => onDuplicate?.()} class="gap-1.5 h-7 text-xs">
			<Copy size={13} />
			Duplicate
		</Button>

		<div class="save-wrap">
			<Button
				size="sm"
				disabled={isSaving}
				onclick={() => onSave?.()}
				class="gap-1.5 h-7 text-xs min-w-[100px]"
			>
				{#if isSaving}
					<Loader2 size={13} class="animate-spin" />
					Saving…
				{:else}
					<Save size={13} />
					Save Engine
				{/if}
			</Button>
			{#if hasUnsavedChanges && !isSaving}
				<span class="dirty-dot"></span>
			{/if}
		</div>

		{#if engine?.id}
			<Button
				variant="ghost"
				size="icon-sm"
				onclick={() => onDelete?.()}
				class="text-muted-foreground hover:text-destructive h-7 w-7"
			>
				<Trash2 size={14} />
			</Button>
		{/if}
	</div>
</div>

<style>
	.topbar {
		height: 52px;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 14px;
		border-bottom: 1px solid var(--border);
		background: var(--card);
		flex-shrink: 0;
		z-index: 10;
	}

	.topbar-left {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
		min-width: 0;
	}

	.name-row {
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.engine-name {
		font-size: 14px;
		font-weight: 600;
		color: var(--foreground);
		max-width: 260px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Save dirty-dot */
	.save-wrap {
		position: relative;
		display: flex;
		flex-shrink: 0;
	}

	.dirty-dot {
		position: absolute;
		top: -3px;
		right: -3px;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--primary);
		border: 2px solid var(--card);
		pointer-events: none;
	}

	/* Right section */
	.topbar-right {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}
</style>
