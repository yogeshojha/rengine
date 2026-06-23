<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import {
		ArrowLeft,
		Save,
		Copy,
		Trash2,
		Download,
		LayoutGrid,
		Code2,
		Loader2,
		Pencil,
		FlaskConical,
		Plus,
		MoreHorizontal,
		Terminal
	} from 'lucide-svelte';
	import type { ScanEngine, Intensity } from '$lib/types/engine';

	const intensityHelp: Record<Intensity, string> = {
		passive: 'No active probing — lowest footprint, stealthiest, fewest findings.',
		normal: 'Balanced active scanning — standard rate limits and tool coverage.',
		aggressive: 'Maximum coverage — higher rate, noisier, most thorough but detectable.'
	};

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
		onToolOptions?: () => void;
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
		onToolOptions,
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
				<Button
					variant="ghost"
					size="icon-sm"
					class="h-6 w-6 text-muted-foreground"
					onclick={startEditName}
				>
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
	<Tooltip.Provider delayDuration={150}>
		<div class="intensity-group">
			<span class="intensity-label">Intensity</span>
			<Tabs.Root
				value={engine?.intensity}
				onValueChange={(v) => onIntensityChange?.(v as Intensity)}
				class="flex-row"
			>
				<Tabs.List class="h-8">
					{#each ['passive', 'normal', 'aggressive'] as const as level (level)}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Tabs.Trigger {...props} value={level} class="text-xs px-3 capitalize">
										{level}
									</Tabs.Trigger>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content class="max-w-[220px] text-xs">
								{intensityHelp[level]}
							</Tooltip.Content>
						</Tooltip.Root>
					{/each}
				</Tabs.List>
			</Tabs.Root>
		</div>
	</Tooltip.Provider>

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
			variant="outline"
			size="sm"
			onclick={() => onToolOptions?.()}
			class="gap-1.5 h-7 text-xs"
		>
			<Terminal size={14} />
			Tool Args
		</Button>

		<Button
			variant={previewMode ? 'default' : 'outline'}
			size="sm"
			onclick={() => onTogglePreview?.()}
			class="gap-1.5 h-7 text-xs"
		>
			<FlaskConical size={14} />
			{previewMode ? 'Exit dry run' : 'Dry run'}
		</Button>

		<Separator
			orientation="vertical"
			class="hidden sm:block data-[orientation=vertical]:h-[18px]"
		/>

		<Button
			variant="outline"
			size="sm"
			onclick={() => onExportYaml?.()}
			class="hidden sm:inline-flex gap-1.5 h-7 text-xs"
		>
			<Download size={13} />
			Export
		</Button>

		<Button
			variant="outline"
			size="sm"
			onclick={() => onDuplicate?.()}
			class="hidden sm:inline-flex gap-1.5 h-7 text-xs"
		>
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
				class="hidden sm:inline-flex text-muted-foreground hover:text-destructive h-7 w-7"
			>
				<Trash2 size={14} />
			</Button>
		{/if}

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon-sm"
						class="sm:hidden h-7 w-7 text-muted-foreground"
						aria-label="More actions"
					>
						<MoreHorizontal size={15} />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-40">
				<DropdownMenu.Item onclick={() => onExportYaml?.()} class="gap-2">
					<Download size={14} />
					Export
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onDuplicate?.()} class="gap-2">
					<Copy size={14} />
					Duplicate
				</DropdownMenu.Item>
				{#if engine?.id}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => onDelete?.()} class="gap-2 text-destructive">
						<Trash2 size={14} />
						Delete
					</DropdownMenu.Item>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</div>

<style>
	.topbar {
		min-height: 52px;
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 10px;
		padding: 8px 14px;
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

	.intensity-group {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.intensity-label {
		font-size: 11px;
		font-weight: 500;
		color: var(--muted-foreground);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		white-space: nowrap;
	}

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

	.topbar-right {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px;
		margin-left: auto;
	}
</style>
