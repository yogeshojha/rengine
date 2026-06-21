<script lang="ts">
	import {
		Globe,
		Share2,
		Building2,
		Search,
		Unlink,
		Cloud,
		Radar,
		Globe2,
		Camera,
		Compass,
		FolderSearch,
		SlidersHorizontal,
		ShieldAlert,
		Lock,
		KeyRound,
		FileText
	} from 'lucide-svelte';
	import { CAPABILITIES, getActiveCapabilities, type Capability, type Phase } from '$lib/types/capabilities';
	import { PHASE_COLORS, ARTIFACT_LABEL, type ScanEngine, type ArtifactType } from '$lib/types/engine';
	import * as Command from '$lib/components/ui/command';
	import { Badge } from '$lib/components/ui/badge';
	import { SvelteSet } from 'svelte/reactivity';

	let {
		open = $bindable(false),
		phase,
		engine,
		onAdd,
		onClose
	}: {
		open: boolean;
		phase: Phase | null;
		engine: ScanEngine;
		onAdd: (capId: string) => void;
		onClose: () => void;
	} = $props();

	const ICONS: Record<string, typeof Globe> = {
		Globe,
		Share2,
		Building2,
		Search,
		Unlink,
		Cloud,
		Radar,
		Globe2,
		Camera,
		Compass,
		FolderSearch,
		SlidersHorizontal,
		ShieldAlert,
		Lock,
		KeyRound,
		FileText
	};

	const PHASE_ORDER: Phase[] = ['discovery', 'expansion', 'depth'];
	const PHASE_TITLE: Record<Phase, string> = {
		discovery: 'Discovery',
		expansion: 'Expansion',
		depth: 'Depth'
	};

	let activePhases = $derived<Phase[]>(phase ? [phase] : PHASE_ORDER);

	let producedArtifacts = $derived.by(() => {
		const set = new SvelteSet<ArtifactType>(['seed']);
		for (const c of getActiveCapabilities(engine)) set.add(c.produces);
		return set;
	});

	function missingInput(cap: Capability): ArtifactType | null {
		for (const a of cap.consumes) if (!producedArtifacts.has(a)) return a;
		return null;
	}

	function addableFor(ph: Phase): Capability[] {
		return CAPABILITIES.filter((c) => c.phase === ph && !c.isActive(engine)).sort(
			(a, b) => a.column - b.column
		);
	}

	let groups = $derived(
		activePhases
			.map((ph) => ({ phase: ph, caps: addableFor(ph) }))
			.filter((g) => g.caps.length > 0)
	);

	function commit(capId: string) {
		onAdd(capId);
		onClose();
	}
</script>

<Command.Dialog
	bind:open
	onOpenChange={(o) => {
		if (!o) onClose();
	}}
>
	<Command.Input placeholder="Add a step…" />
	<Command.List>
		<Command.Empty>No steps found.</Command.Empty>
		{#each groups as group (group.phase)}
			{@const pc = PHASE_COLORS[group.phase]}
			<Command.Group>
				<div class="grp-heading" data-command-group-heading>
					<span class="grp-dot" style="background: {pc.accent};"></span>
					{PHASE_TITLE[group.phase]}
				</div>
				{#each group.caps as cap (cap.id)}
					{@const Icon = ICONS[cap.icon] ?? FileText}
					{@const needsKey = (cap.needsKeyTools?.length ?? 0) > 0}
					{@const missing = missingInput(cap)}
					<Command.Item
						value={cap.label + ' ' + cap.tools.join(' ')}
						onSelect={() => commit(cap.id)}
					>
						<span class="row-icon" class:row-dim={missing}>
							<Icon size={15} />
						</span>
						<span class="row-body" class:row-dim={missing}>
							<span class="row-top">
								<span class="row-label">{cap.label}</span>
								{#if needsKey}
									<KeyRound class="key-glyph" size={11} aria-label="Needs API key" />
								{/if}
							</span>
							{#if missing}
								<span class="row-desc">requires {ARTIFACT_LABEL[missing]}</span>
							{:else}
								<span class="row-desc">{cap.description}</span>
							{/if}
						</span>
						<span class="row-right">
							<Badge variant="secondary">{cap.producesNoun}</Badge>
						</span>
					</Command.Item>
				{/each}
			</Command.Group>
		{/each}
	</Command.List>
</Command.Dialog>

<style>
	.grp-heading {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 8px;
		font-size: 12px;
		font-weight: 500;
		color: var(--muted-foreground);
	}

	.grp-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.row-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 7px;
		flex-shrink: 0;
		background: var(--muted);
		color: var(--muted-foreground);
	}

	.row-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.row-top {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	.row-label {
		font-size: 13px;
		font-weight: 500;
		color: var(--foreground);
		line-height: 1.2;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.row-body :global(.key-glyph) {
		color: var(--muted-foreground);
		flex-shrink: 0;
	}

	.row-desc {
		font-size: 11px;
		color: var(--muted-foreground);
		line-height: 1.3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.row-right {
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.row-dim {
		opacity: 0.5;
	}
</style>
