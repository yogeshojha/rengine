<script lang="ts">
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Switch } from '$lib/components/ui/switch';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Hint from '$lib/components/hint.svelte';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import StageFieldRow from './stage-field.svelte';
	import type { StageCatalogEntry, StageConfig, StageField } from '$lib/types/scan-engine';
	import { advancedFields, basicFields, targetTypeLabel } from '$lib/types/scan-engine';

	interface Props {
		stage: StageCatalogEntry;
		config: StageConfig;
		open: boolean;
		active: boolean;
		applicable: boolean;
		blockedByIntensity: boolean;
		lensTargetType: string | null;
		support?: boolean;
		onToggleOpen: () => void;
		onChange: (field: string, value: unknown) => void;
		onReset: () => void;
	}

	let {
		stage,
		config,
		open,
		active,
		applicable,
		blockedByIntensity,
		lensTargetType,
		support = false,
		onToggleOpen,
		onChange,
		onReset
	}: Props = $props();

	let advancedOpen = $state(false);

	const alwaysOn = $derived(Boolean(stage.always_on));
	const enabled = $derived(alwaysOn || Boolean(config.enabled ?? stage.defaults.enabled));
	const dimmed = $derived(!applicable || blockedByIntensity);
	const nodeState = $derived(!enabled ? 'off' : dimmed ? 'dim' : 'on');

	const basic = $derived(basicFields(stage));
	const advanced = $derived(advancedFields(stage));

	const changed = $derived(
		stage.fields.filter((f) => {
			const current = config[f.name];
			if (current === undefined) return false;
			return JSON.stringify(current) !== JSON.stringify(stage.defaults[f.name]);
		})
	);
	const advancedChanged = $derived(changed.filter((f) => f.tier === 'advanced').length);

	function describe(field: StageField, value: unknown): string | null {
		if (value === undefined || value === null || value === '') return null;
		if (Array.isArray(value)) {
			return value.length ? `${value.length} ${field.title.toLowerCase()}` : null;
		}
		if (typeof value === 'boolean') return value ? field.title.toLowerCase() : null;
		if (typeof value === 'number') return `${field.title.toLowerCase()} ${value.toLocaleString()}`;
		return field.option_labels?.[String(value)] ?? String(value);
	}

	const summary = $derived.by(() => {
		const parts: string[] = [];
		for (const field of basic) {
			const text = describe(field, config[field.name] ?? stage.defaults[field.name]);
			if (text) parts.push(text);
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
	data-support={support}
>
	<div class="head">
		{#if support}
			{#if alwaysOn}
				<Hint text="Always on">
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<Checkbox checked disabled aria-label="{stage.title} is always on" />
						</span>
					{/snippet}
				</Hint>
			{:else}
				<Checkbox
					checked={enabled}
					onCheckedChange={(v) => onChange('enabled', Boolean(v))}
					aria-label="Enable {stage.title}"
				/>
			{/if}
		{:else}
			<span class="node" data-state={nodeState} aria-hidden="true"></span>
		{/if}

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

			{#if !support}
				{#if alwaysOn}
					<Hint text="Always on">
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<Switch checked disabled aria-label="{stage.title} is always on" />
							</span>
						{/snippet}
					</Hint>
				{:else}
					<Switch
						checked={enabled}
						onCheckedChange={(v) => onChange('enabled', v)}
						aria-label="Enable {stage.title}"
					/>
				{/if}
			{/if}
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

		{#if basic.length}
			<div class="fields">
				{#each basic as field (field.name)}
					<StageFieldRow
						{field}
						stageName={stage.name}
						value={config[field.name]}
						onChange={(v) => onChange(field.name, v)}
					/>
				{/each}
			</div>
		{:else if !advanced.length}
			<p class="desc">No settings.</p>
		{/if}

		{#if advanced.length}
			<Collapsible.Root bind:open={advancedOpen} class="advanced">
				<Collapsible.Trigger class="advanced-head">
					<ChevronRight size={12} class="chev" />
					<span>Advanced</span>
					<span class="advanced-count">
						{advanced.length} setting{advanced.length === 1 ? '' : 's'}{advancedChanged
							? ` · ${advancedChanged} changed`
							: ''}
					</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="fields">
						{#each advanced as field (field.name)}
							<StageFieldRow
								{field}
								stageName={stage.name}
								value={config[field.name]}
								onChange={(v) => onChange(field.name, v)}
							/>
						{/each}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
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
	:global(.row[data-support='true']) {
		background: color-mix(in oklch, var(--muted) 30%, transparent);
	}
	:global(.row[data-support='true']) .title {
		font-weight: 450;
	}

	.head {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 14px 0 12px;
		min-height: 46px;
	}
	:global(.row[data-support='true']) .head {
		min-height: 40px;
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
	:global(.row[data-state='open'] > .head .disclose .chev) {
		transform: rotate(90deg);
	}
	.title {
		font-size: 14px;
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
		max-width: 260px;
		font-variant-numeric: tabular-nums;
	}
	.meta :global(.tag) {
		font-size: 11px;
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
		font-size: 11px;
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
	:global(.row .advanced) {
		margin-top: 6px;
		border-top: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
	}
	:global(.row .advanced-head) {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: 10px 0 6px;
		background: none;
		border: none;
		cursor: pointer;
		color: var(--muted-foreground);
		font-size: 12px;
		font-weight: 500;
	}
	:global(.row .advanced[data-state='open'] .advanced-head .chev) {
		transform: rotate(90deg);
	}
	.advanced-count {
		font-weight: 400;
		font-variant-numeric: tabular-nums;
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
