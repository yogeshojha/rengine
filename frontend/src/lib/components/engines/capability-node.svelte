<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';
	import {
		Globe,
		Share2,
		Building2,
		Search,
		Unlink,
		Cloud,
		Radar,
		Globe2,
		Compass,
		FolderSearch,
		SlidersHorizontal,
		ShieldAlert,
		KeyRound,
		FileText,
		Settings2,
		X,
		Check,
		ArrowRight
	} from 'lucide-svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { PHASE_COLORS } from '$lib/types/engine';
	import type { Phase } from '$lib/types/capabilities';
	import type { Severity } from '$lib/types/severity';

	interface CapNodeData extends Record<string, unknown> {
		capId: string;
		label: string;
		producesNoun: string;
		phase: Phase;
		required: boolean;
		enabled: boolean;
		icon: string;
		needsKey: boolean;
		severityDots?: Severity[];
		previewState?: 'run' | 'skip-disabled' | 'skip-key' | null;
		previewHint?: string;
		onToggle: (capId: string, enabled: boolean) => void;
		onConfigure: (capId: string) => void;
		onDelete: (capId: string) => void;
	}

	let { data, selected }: NodeProps = $props();
	let d = $derived(data as unknown as CapNodeData);
	let accent = $derived(PHASE_COLORS[d.phase].accent);

	const DESCRIPTIONS: Record<string, string> = {
		'dns-whois': 'Resolve hosts, DNS records & WHOIS',
		'related-domains': 'Find related domains for the org',
		'org-asn': 'Map org domains & netblocks',
		'subdomain-enum': 'Find all subdomains',
		'takeover-dns': 'Check for subdomain takeovers',
		'cloud-recon': 'Find exposed cloud buckets',
		'port-scan': 'Discover open ports & services',
		'http-probe': 'Probe live web services',
		'url-discovery': 'Crawl endpoints & URLs',
		'dir-fuzz': 'Fuzz for hidden paths & files',
		'param-vhost': 'Discover hidden params & vhosts',
		'vuln-scan': 'Template-based vulnerability scanning',
		'js-secrets': 'Extract leaked secrets from JS',
		reporting: 'Build report & send alerts'
	};
	let description = $derived(DESCRIPTIONS[d.capId] ?? `Produce ${d.producesNoun}`);

	let sevDots = $derived(
		d.capId === 'vuln-scan' && d.severityDots?.length ? d.severityDots.slice(0, 4) : []
	);

	function handleBody() {
		d.onConfigure(d.capId);
	}
	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			d.onConfigure(d.capId);
		}
	}
	function stop(e: Event) {
		e.stopPropagation();
	}
</script>

<div
	class="cap-node"
	class:is-disabled={!d.enabled}
	class:is-selected={selected}
	style="--accent: {accent};"
	role="button"
	tabindex="0"
	aria-label="Configure {d.label}"
	onclick={handleBody}
	onkeydown={handleKey}
>
	<Handle type="target" position={Position.Left} class="cap-handle" />

	<span class="accent-rail" aria-hidden="true"></span>

	<div class="cap-head">
		<div class="icon-chip">
			{#if d.icon === 'Globe'}
				<Globe size={15} />
			{:else if d.icon === 'Share2'}
				<Share2 size={15} />
			{:else if d.icon === 'Building2'}
				<Building2 size={15} />
			{:else if d.icon === 'Search'}
				<Search size={15} />
			{:else if d.icon === 'Unlink'}
				<Unlink size={15} />
			{:else if d.icon === 'Cloud'}
				<Cloud size={15} />
			{:else if d.icon === 'Radar'}
				<Radar size={15} />
			{:else if d.icon === 'Globe2'}
				<Globe2 size={15} />
			{:else if d.icon === 'Compass'}
				<Compass size={15} />
			{:else if d.icon === 'FolderSearch'}
				<FolderSearch size={15} />
			{:else if d.icon === 'SlidersHorizontal'}
				<SlidersHorizontal size={15} />
			{:else if d.icon === 'ShieldAlert'}
				<ShieldAlert size={15} />
			{:else if d.icon === 'KeyRound'}
				<KeyRound size={15} />
			{:else if d.icon === 'FileText'}
				<FileText size={15} />
			{:else}
				<Globe size={15} />
			{/if}
			<span class="phase-dot" aria-hidden="true"></span>
		</div>

		<div class="cap-title">{d.label}</div>

		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="cap-tools" onclick={stop}>
			<Button
				variant="ghost"
				size="icon"
				class="tool-btn"
				title="Configure"
				onclick={(e) => {
					stop(e);
					d.onConfigure(d.capId);
				}}
			>
				<Settings2 size={13} />
			</Button>
			{#if !d.required}
				<Button
					variant="ghost"
					size="icon"
					class="tool-btn"
					title="Remove step"
					onclick={(e) => {
						stop(e);
						d.onDelete(d.capId);
					}}
				>
					<X size={13} />
				</Button>
			{/if}
		</div>
	</div>

	<div class="cap-desc">{description}</div>

	<div class="cap-foot">
		<span class="produces"><ArrowRight size={11} />{d.producesNoun}</span>
		<div class="foot-right">
			{#if sevDots.length}
				<span class="sev-row" title="Severity coverage">
					{#each sevDots as sev, i (`${sev}-${i}`)}
						<span class="sev-dot" class:strong={i < 2}></span>
					{/each}
				</span>
			{/if}
			{#if d.needsKey}
				<a
					href="/settings?tab=api-keys"
					class="key-link"
					title="This source needs an API key — configure it in Settings"
					onclick={stop}
				>
					<Badge variant="outline" class="key-badge">
						<KeyRound size={10} />API key
					</Badge>
				</a>
			{/if}
		</div>
	</div>

	{#if d.previewState === 'run'}
		<div class="preview preview-run">
			<Check size={11} class="run-check" />will run
		</div>
	{:else if d.previewState === 'skip-disabled' || d.previewState === 'skip-key'}
		<div class="preview preview-skip">{d.previewHint ?? 'skipped'}</div>
	{/if}

	<Handle type="source" position={Position.Right} class="cap-handle" />
</div>

<style>
	.cap-node {
		position: relative;
		width: 264px;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.75rem;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
		cursor: pointer;
		user-select: none;
		overflow: hidden;
		transition:
			border-color 0.14s ease,
			box-shadow 0.14s ease,
			transform 0.14s ease,
			opacity 0.14s ease;
	}
	.cap-node:hover {
		border-color: color-mix(in oklch, var(--ring) 55%, transparent);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		transform: translateY(-1px);
	}
	.cap-node:focus-visible {
		outline: none;
		border-color: var(--ring);
		box-shadow: 0 0 0 2px var(--ring);
	}
	.is-disabled {
		opacity: 0.6;
	}
	.is-disabled .accent-rail {
		background: var(--border);
	}
	.is-selected {
		border-color: var(--ring);
		box-shadow:
			0 0 0 2px var(--ring),
			0 6px 16px rgba(0, 0, 0, 0.12);
	}
	.is-selected:hover {
		border-color: var(--ring);
	}
	.is-selected .accent-rail {
		width: 3px;
		filter: brightness(1.12);
	}

	.accent-rail {
		position: absolute;
		top: 0;
		left: 0;
		bottom: 0;
		width: 2px;
		background: var(--accent);
		transition:
			width 0.14s ease,
			filter 0.14s ease;
	}

	.cap-head {
		position: relative;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 9px 10px 0 12px;
	}
	.icon-chip {
		position: relative;
		width: 28px;
		height: 28px;
		flex-shrink: 0;
		border-radius: 7px;
		background: var(--secondary);
		color: var(--foreground);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.phase-dot {
		position: absolute;
		top: -2px;
		right: -2px;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--accent);
		box-shadow: 0 0 0 2px var(--card);
	}
	.cap-title {
		flex: 1;
		min-width: 0;
		font-size: 13px;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--foreground);
		line-height: 1.15;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.cap-tools {
		position: absolute;
		top: 9px;
		right: 10px;
		display: flex;
		align-items: center;
		gap: 2px;
		height: 28px;
		padding-left: 14px;
		background: var(--card);
		opacity: 0;
		transform: translateX(4px);
		pointer-events: none;
		transition:
			opacity 0.12s ease,
			transform 0.12s ease;
	}
	.cap-tools::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 100%;
		width: 22px;
		background: linear-gradient(to right, transparent, var(--card));
		pointer-events: none;
	}
	.cap-node:hover .cap-tools,
	.cap-node.is-selected .cap-tools,
	.cap-node:focus-within .cap-tools {
		opacity: 1;
		transform: translateX(0);
		pointer-events: auto;
	}
	.cap-node :global(.tool-btn) {
		width: 22px;
		height: 22px;
		color: var(--muted-foreground);
	}
	.cap-node :global(.tool-btn:hover) {
		color: var(--foreground);
	}

	.cap-desc {
		padding: 6px 12px 0 12px;
		font-size: 12px;
		color: var(--muted-foreground);
		line-height: 1.35;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.cap-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 8px 10px 10px 12px;
	}
	.produces {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		min-width: 0;
		font-size: 11px;
		color: var(--muted-foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.produces :global(svg) {
		flex-shrink: 0;
		opacity: 0.8;
	}
	.foot-right {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}
	.sev-row {
		display: inline-flex;
		align-items: center;
		gap: 3px;
	}
	.sev-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--muted-foreground);
		opacity: 0.45;
	}
	.sev-dot.strong {
		opacity: 1;
		background: var(--foreground);
	}
	.key-link {
		display: inline-flex;
		text-decoration: none;
		border-radius: 0.5rem;
	}
	.key-link:focus-visible {
		outline: none;
		box-shadow: 0 0 0 2px var(--ring);
	}
	.cap-node :global(.key-badge) {
		gap: 3px;
		padding: 1px 6px;
		font-size: 10px;
		font-weight: 500;
		color: var(--muted-foreground);
		border-color: var(--border);
		cursor: pointer;
		transition:
			color 0.12s ease,
			border-color 0.12s ease;
	}
	.key-link:hover :global(.key-badge) {
		color: var(--foreground);
		border-color: color-mix(in oklch, var(--ring) 55%, transparent);
	}

	.preview {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 5px 12px;
		font-size: 11px;
		font-weight: 500;
		border-top: 1px solid var(--border);
	}
	.preview-run {
		color: var(--foreground);
	}
	.preview-run :global(.run-check) {
		color: var(--foreground);
	}
	.preview-skip {
		color: var(--muted-foreground);
	}

	.cap-node :global(.cap-handle) {
		width: 9px;
		height: 9px;
		background: var(--muted-foreground);
		border: 2px solid var(--card);
	}
</style>
