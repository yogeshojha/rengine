<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Clock from '@lucide/svelte/icons/clock';
	import type { ScanContextRead } from '$lib/types/scan-context';
	import { authBadgeLabel, countExclusions, countOverrides } from './context-summary';
	import { formatDistanceToNow } from '$lib/utilities/dates';

	interface Props {
		context: ScanContextRead;
		onEdit?: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
	}

	let { context, onEdit, onDuplicate, onDelete }: Props = $props();

	let chips = $derived.by(() => {
		const out: string[] = [];
		if (context.extra_headers.length > 0) {
			out.push(
				`${context.extra_headers.length} header${context.extra_headers.length === 1 ? '' : 's'}`
			);
		}
		if (context.global_rate_limit_override != null) {
			out.push(`rate ${context.global_rate_limit_override}/s`);
		}
		const tools = Object.keys(context.per_tool_rate_overrides).length;
		if (tools > 0) out.push(`${tools} tool rate${tools === 1 ? '' : 's'}`);
		const excl = countExclusions(context);
		if (excl > 0) out.push(`${excl} exclusion${excl === 1 ? '' : 's'}`);
		return out;
	});

	let overrideCount = $derived(countOverrides(context));
</script>

<div
	class="card"
	role="button"
	tabindex={0}
	onclick={() => onEdit?.()}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onEdit?.();
		}
	}}
>
	<div class="rail"></div>
	<div class="card-body">
		<div class="card-header">
			<div class="name-block">
				<h3 class="ctx-name">{context.name}</h3>
				<Badge variant="outline" class="auth-badge">{authBadgeLabel(context)}</Badge>
			</div>
			<div class="actions">
				<Button
					variant="ghost"
					size="icon-sm"
					onclick={(e) => {
						e.stopPropagation();
						onDuplicate?.();
					}}
				>
					<Copy size={13} />
				</Button>
				<Button
					variant="ghost"
					size="icon-sm"
					class="text-destructive hover:text-destructive"
					onclick={(e) => {
						e.stopPropagation();
						onDelete?.();
					}}
				>
					<Trash2 size={13} />
				</Button>
			</div>
		</div>

		{#if context.description}
			<p class="description">{context.description}</p>
		{/if}

		{#if chips.length > 0}
			<div class="chip-row">
				{#each chips as chip (chip)}
					<Badge
						variant="secondary"
						class="rounded-sm border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
						>{chip}</Badge
					>
				{/each}
			</div>
		{:else}
			<p class="passthrough">Pass-through — no overrides</p>
		{/if}

		<div class="card-footer">
			<div class="footer-left">
				<Clock size={12} class="footer-icon" />
				<span class="ts">
					{#if context.last_used_at}
						Used {formatDistanceToNow(context.last_used_at)} ago
					{:else}
						Never used
					{/if}
				</span>
			</div>
			<span class="override-count">
				{overrideCount} override{overrideCount === 1 ? '' : 's'}
			</span>
		</div>
	</div>
</div>

<style>
	.card {
		position: relative;
		display: flex;
		border-radius: 10px;
		border: 1px solid var(--border);
		background: var(--card);
		overflow: hidden;
		box-shadow: var(--shadow-sm);
		transition:
			box-shadow 0.2s,
			transform 0.15s,
			border-color 0.2s;
		cursor: pointer;
	}

	.card:hover {
		box-shadow: var(--shadow-md);
		transform: translateY(-1px);
		border-color: var(--ring);
	}

	.rail {
		width: 3px;
		background: var(--muted-foreground);
		opacity: 0.45;
		flex-shrink: 0;
	}

	.card-body {
		flex: 1;
		min-width: 0;
		padding: 14px 16px;
	}

	.card-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 8px;
	}

	.name-block {
		display: flex;
		align-items: center;
		gap: 7px;
		flex-wrap: wrap;
		flex: 1;
		min-width: 0;
	}

	.ctx-name {
		font-size: 14px;
		font-weight: 700;
		color: var(--foreground);
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:global(.auth-badge) {
		padding: 1px 8px;
		font-size: 10px;
		font-weight: 600;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: 2px;
		flex-shrink: 0;
	}

	.description {
		font-size: 12px;
		color: var(--muted-foreground);
		margin: 0 0 8px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.chip-row {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-bottom: 12px;
		flex-wrap: wrap;
	}

	.passthrough {
		font-size: 11px;
		color: var(--muted-foreground);
		font-style: italic;
		margin: 0 0 12px;
	}

	.card-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-top: 10px;
		border-top: 1px solid var(--border);
	}

	.footer-left {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	:global(.footer-icon) {
		color: var(--muted-foreground);
	}

	.ts {
		font-size: 11px;
		color: var(--muted-foreground);
	}

	.override-count {
		font-size: 11px;
		color: var(--muted-foreground);
	}
</style>
