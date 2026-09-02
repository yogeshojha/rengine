<script lang="ts">
	import { slide } from 'svelte/transition';
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

	interface Props {
		stage: StageCatalogEntry;
		config: StageConfig;
		open: boolean;
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
		applicable,
		blockedByIntensity,
		lensTargetType,
		onToggleOpen,
		onChange,
		onReset
	}: Props = $props();

	const enabled = $derived(Boolean(config.enabled ?? stage.defaults.enabled));

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

<div class="row" class:dimmed={!applicable || blockedByIntensity} class:open>
	<div class="head">
		<button type="button" class="disclose" onclick={onToggleOpen} aria-expanded={open}>
			<ChevronRight size={14} class="chev" />
			<span class="title">{stage.title}</span>
		</button>

		<div class="meta">
			{#if blockedByIntensity}
				<Badge variant="outline" class="tag">Blocked by passive intensity</Badge>
			{:else if !applicable && lensTargetType}
				<Badge variant="outline" class="tag"
					>{stage.applies_to.map(targetTypeLabel).join(' · ')} only</Badge
				>
			{:else if enabled && summary}
				<span class="summary">{summary}</span>
			{/if}

			{#if changed.length}
				<Badge variant="secondary" class="tag">{changed.length} changed</Badge>
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
						Uses API keys: {stage.api_keys.join(', ')}
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

	{#if open}
		<div class="body" transition:slide={{ duration: 140 }}>
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
				<p class="desc">No settings — this stage is on or off.</p>
			{/if}

			{#if changed.length}
				<div class="foot">
					<Button variant="ghost" size="sm" class="h-7 gap-1.5 text-xs" onclick={onReset}>
						<RotateCcw size={12} />
						Reset to defaults
					</Button>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.row {
		border-bottom: 1px solid var(--border);
	}
	.row:last-child {
		border-bottom: none;
	}
	.row.dimmed .title,
	.row.dimmed .summary {
		opacity: 0.5;
	}

	.head {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0 14px 0 6px;
		min-height: 46px;
	}

	.disclose {
		display: flex;
		align-items: center;
		gap: 6px;
		flex: 1;
		min-width: 0;
		padding: 12px 4px;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		color: inherit;
	}
	.disclose :global(.chev) {
		flex-shrink: 0;
		color: var(--muted-foreground);
		transition: transform 0.14s ease;
	}
	.row.open .disclose :global(.chev) {
		transform: rotate(90deg);
	}
	.title {
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
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

	.body {
		padding: 2px 14px 14px 26px;
	}
	.desc {
		font-size: 12px;
		color: var(--muted-foreground);
		margin-bottom: 10px;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-bottom: 6px;
	}
	.tool {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 10px;
		color: var(--muted-foreground);
		background: var(--muted);
		border-radius: 4px;
		padding: 2px 6px;
	}
	.fields {
		display: flex;
		flex-direction: column;
	}
	.fields > :global(* + *) {
		border-top: 1px solid color-mix(in oklch, var(--border) 55%, transparent);
	}
	.foot {
		margin-top: 8px;
		padding-top: 8px;
		border-top: 1px solid color-mix(in oklch, var(--border) 55%, transparent);
	}
</style>
