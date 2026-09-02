<script lang="ts">
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Switch } from '$lib/components/ui/switch';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import StageFieldRow from './stage-field.svelte';
	import type { StageCatalogEntry, StageConfig } from '$lib/types/scan-engine';
	import { targetTypeLabel } from '$lib/types/scan-engine';

	type RailKind = 'none' | 'solid' | 'dotted';

	interface Props {
		stage: StageCatalogEntry;
		config: StageConfig;
		open: boolean;
		active: boolean;
		railUp?: RailKind;
		railDown?: RailKind;
		applicable: boolean;
		blockedByIntensity: boolean;
		lensTargetType: string | null;
		onToggleOpen: () => void;
		onChange: (field: string, value: unknown) => void;
		onReset: () => void;
	}

	let {
		stage,
		config,
		open,
		active,
		railUp = 'none',
		railDown = 'none',
		applicable,
		blockedByIntensity,
		lensTargetType,
		onToggleOpen,
		onChange,
		onReset
	}: Props = $props();

	const enabled = $derived(Boolean(config.enabled ?? stage.defaults.enabled));
	const dimmed = $derived(!applicable || blockedByIntensity);
	const nodeState = $derived(!enabled ? 'off' : dimmed ? 'dim' : 'on');

	const settingFields = $derived(stage.fields.filter((f) => f.name !== 'enabled'));

	const changed = $derived(
		stage.fields.filter((f) => {
			const current = config[f.name];
			if (current === undefined) return false;
			return JSON.stringify(current) !== JSON.stringify(stage.defaults[f.name]);
		})
	);

	const summary = $derived.by(() => {
		const parts: string[] = [];
		for (const field of settingFields.slice(0, 6)) {
			const value = config[field.name] ?? stage.defaults[field.name];
			if (value === undefined || value === null || value === '') continue;
			if (Array.isArray(value)) {
				if (value.length) parts.push(`${value.length} ${field.title.toLowerCase()}`);
			} else if (typeof value === 'boolean') {
				if (value) parts.push(field.title.toLowerCase());
			} else if (field.scale === 'rate') {
				parts.push(`${value}/s`);
			} else if (field.scale === 'threads') {
				parts.push(`${value} threads`);
			} else if (field.scale === 'timeout') {
				parts.push(`${value}s`);
			} else {
				parts.push(String(value));
			}
		}
		return parts.slice(0, 3).join(' · ');
	});
</script>

<Collapsible.Root
	{open}
	onOpenChange={() => onToggleOpen()}
	class="row"
	data-active={active}
	data-dim={dimmed}
	data-enabled={enabled}
>
	<span class="rail up" data-kind={railUp} aria-hidden="true"></span>
	<span class="rail down" data-kind={railDown} aria-hidden="true"></span>
	<div class="head">
		<span class="node" data-state={nodeState} aria-hidden="true"></span>

		<Collapsible.Trigger class="disclose" aria-label="{open ? 'Collapse' : 'Expand'} {stage.title}">
			<ChevronRight size={14} class="chev" />
			<span class="title">{stage.title}</span>
			{#if changed.length}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="mod" aria-label="{changed.length} settings changed"></span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="text-xs">
						{changed.length} setting{changed.length === 1 ? '' : 's'} differ from defaults
					</Tooltip.Content>
				</Tooltip.Root>
			{/if}
		</Collapsible.Trigger>

		<div class="meta">
			{#if blockedByIntensity}
				<Badge variant="outline" class="tag">Skipped at passive</Badge>
			{:else if !applicable && lensTargetType}
				<Badge variant="outline" class="tag">
					{stage.applies_to.map(targetTypeLabel).join(' · ')} only
				</Badge>
			{:else if enabled && summary}
				<span class="summary">{summary}</span>
			{/if}

			{#if !stage.touches_target}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="icon-note"><EyeOff size={12} /></span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="text-xs">Sends no traffic to the target</Tooltip.Content>
				</Tooltip.Root>
			{/if}

			{#if stage.api_keys.length}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="icon-note"><KeyRound size={12} /></span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="text-xs">
						{stage.requires_api_keys ? 'Needs' : 'Uses'} API keys: {stage.api_keys.join(', ')}
					</Tooltip.Content>
				</Tooltip.Root>
			{/if}

			<Switch
				checked={enabled}
				onCheckedChange={(v) => onChange('enabled', v)}
				aria-label="Enable {stage.title}"
			/>
		</div>
	</div>

	<Collapsible.Content class="body">
		<p class="desc">{stage.description}</p>

		{#if stage.tools.length}
			<div class="tools">
				{#each stage.tools as tool (tool)}
					<span class="tool">{tool}</span>
				{/each}
			</div>
		{/if}

		{#if settingFields.length}
			<div class="fields">
				{#each settingFields as field (field.name)}
					<StageFieldRow
						{field}
						stageName={stage.name}
						value={config[field.name]}
						onChange={(v) => onChange(field.name, v)}
					/>
				{/each}
			</div>
		{:else}
			<p class="desc">This stage has no configurable settings.</p>
		{/if}

		{#if changed.length}
			<div class="foot">
				<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" onclick={onReset}>
					<RotateCcw size={12} />
					Reset stage to defaults
				</Button>
			</div>
		{/if}
	</Collapsible.Content>
</Collapsible.Root>

<style>
	:global(.row) {
		position: relative;
		border-bottom: 1px solid var(--border);
		transition: background 0.15s ease;
	}
	:global(.row:last-child) {
		border-bottom: none;
	}
	:global(.row[data-active='true']) {
		background: color-mix(in oklch, var(--primary) 4%, transparent);
	}
	:global(.row[data-active='true'])::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		background: var(--primary);
		opacity: 0.6;
	}
	:global(.row[data-dim='true']) .title,
	:global(.row[data-dim='true']) .summary,
	:global(.row[data-enabled='false']) .title {
		color: var(--muted-foreground);
	}

	.head {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 14px 0 12px;
		min-height: 46px;
	}

	.node {
		position: relative;
		z-index: 1;
		width: 9px;
		height: 9px;
		border-radius: 999px;
		flex-shrink: 0;
		box-shadow: 0 0 0 3px var(--card);
		background: var(--card);
		border: 1.5px solid var(--muted-foreground);
	}
	.node[data-state='on'] {
		background: var(--primary);
		border-color: var(--primary);
	}
	.node[data-state='dim'] {
		background: color-mix(in oklch, var(--muted-foreground) 35%, transparent);
		border-color: transparent;
	}
	.rail {
		position: absolute;
		left: 15px;
		width: 3px;
		pointer-events: none;
	}
	.rail.up {
		top: 0;
		height: 23px;
	}
	.rail.down {
		top: 23px;
		bottom: 0;
	}
	.rail[data-kind='none'] {
		display: none;
	}
	.rail[data-kind='solid'] {
		background: linear-gradient(var(--border), var(--border)) center / 1px 100% no-repeat;
	}
	.rail[data-kind='dotted'] {
		background: radial-gradient(
				circle,
				color-mix(in oklch, var(--muted-foreground) 65%, transparent) 1px,
				transparent 1.6px
			)
			center / 3px 5px repeat-y;
	}

	:global(.row .disclose) {
		display: flex;
		align-items: center;
		gap: 6px;
		flex: 1;
		min-width: 0;
		padding: 13px 4px 13px 0;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		color: inherit;
	}
	:global(.row .disclose .chev) {
		flex-shrink: 0;
		color: var(--muted-foreground);
		transition: transform 0.15s ease;
	}
	:global(.row[data-state='open'] .disclose .chev) {
		transform: rotate(90deg);
	}
	.title {
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.mod {
		display: inline-block;
		width: 6px;
		height: 6px;
		border-radius: 999px;
		background: var(--primary);
		flex-shrink: 0;
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}
	.summary {
		font-size: 11px;
		color: var(--muted-foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 240px;
		font-variant-numeric: tabular-nums;
	}
	.meta :global(.tag) {
		font-size: 10px;
		font-weight: 400;
		padding: 1px 6px;
	}
	.icon-note {
		display: inline-flex;
		color: var(--muted-foreground);
	}

	:global(.row .body) {
		padding: 0 16px 14px 32px;
	}
	.desc {
		font-size: 12px;
		color: var(--muted-foreground);
		margin-bottom: 10px;
		line-height: 1.5;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 8px;
	}
	.tool {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 10.5px;
		line-height: 18px;
		color: var(--muted-foreground);
		background: var(--muted);
		border-radius: 4px;
		padding: 0 6px;
	}
	.fields {
		display: flex;
		flex-direction: column;
	}
	.fields > :global(* + *) {
		border-top: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
	}
	.foot {
		margin-top: 8px;
		padding-top: 8px;
		border-top: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
	}

	@media (max-width: 640px) {
		.summary {
			display: none;
		}
		:global(.row .body) {
			padding-left: 16px;
		}
	}
</style>
