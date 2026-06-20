<script lang="ts" module>
	import CapabilityNode from './capability-node.svelte';
	import SeedNode from './seed-node.svelte';
	import ReconNode from './recon-node.svelte';
	import ArtifactEdge from './artifact-edge.svelte';

	// Created ONCE at module scope — recreating per render triggers the
	// "new nodeTypes object" warning from SvelteFlow.
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const nodeTypes: any = {
		capabilityNode: CapabilityNode,
		seedCard: SeedNode,
		reconData: ReconNode
	};
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const edgeTypes: any = {
		artifact: ArtifactEdge
	};
</script>

<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteFlowProvider, ViewportPortal, MarkerType } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { Wand2, Plus } from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';

	import EngineFlow from './engine-flow.svelte';
	import AddStepPalette from './add-step-palette.svelte';

	import {
		PHASE_COLORS,
		ARTIFACT_LABEL,
		type ArtifactType,
		type ScanEngine
	} from '$lib/types/engine';
	import {
		CAPABILITIES,
		PHASE_COLUMN_RANGE,
		getActiveCapabilities,
		getReconOutputs,
		applyEnableCapability,
		applyDisableCapability,
		type Capability,
		type Phase
	} from '$lib/types/capabilities';

	interface Props {
		engine: ScanEngine;
		selectedCapabilityId: string | null;
		previewMode?: boolean;
		// nonce — when it increments, open the all-phases palette (topbar "+ Add Step")
		requestAddOpen?: number;
		onCapabilitySelected?: (capId: string | null) => void;
		onEngineChange?: (updated: ScanEngine) => void;
	}

	let {
		engine,
		selectedCapabilityId,
		previewMode = false,
		requestAddOpen = 0,
		onCapabilitySelected,
		onEngineChange
	}: Props = $props();

	// ── Layout math (x = execution order) ───────────────────────────────────────
	const COL_GAP = 360;
	const NODE_W = 264;
	const NODE_H = 92;
	const ROW_GAP = 180;
	const CENTER_Y = 400;
	// horizontal inset of each band from its leftmost/rightmost node card
	const PAD = 18;
	// minimum tall-band height + extra vertical breathing around the node span
	const BAND_MIN_HEIGHT = 430;
	const BAND_SPAN_PAD = 170;
	// gutter taken out of each band; with COL_GAP 360 this leaves ~84px between
	// adjacent phase bands (vs ~96px between nodes within a phase) — enough room for
	// the cross-phase artifact label to sit in the gutter without touching either band.
	const BAND_GUTTER = 24;

	function columnX(col: number): number {
		return col * COL_GAP;
	}

	// ── Phase metadata ──────────────────────────────────────────────────────────
	const PHASE_ORDER: Phase[] = ['discovery', 'expansion', 'depth'];
	const PHASE_TITLE: Record<Phase, string> = {
		discovery: 'Discovery',
		expansion: 'Expansion',
		depth: 'Depth'
	};
	const PHASE_NUM: Record<Phase, number> = { discovery: 1, expansion: 2, depth: 3 };

	// CRITICAL: counts (and band membership) key off cap.phase, NOT a column-range
	// lookup. url-discovery/dir-fuzz/param-vhost sit in col5 but belong to the
	// EXPANSION band by phase; takeover-dns/tls-ssl sit in col6 and belong to the
	// DEPTH band by phase. The band rectangle still spans PHASE_COLUMN_RANGE columns
	// for x-geometry, but a node's band membership is decided by .phase.
	function phaseCounts(active: Capability[], phase: Phase) {
		const inPhase = (c: Capability) => c.phase === phase;
		return {
			active: active.filter(inPhase).length,
			total: CAPABILITIES.filter(inPhase).length
		};
	}

	// ── Node id helpers ───────────────────────────────────────────────────────────
	function nodeId(capId: string) {
		return `cap-${capId}`;
	}

	// ── Pure column layout (id -> position) ─────────────────────────────────────
	// The canonical layout used on first build and on Tidy up.
	function computeLayout(active: Capability[]): {
		pos: Record<string, { x: number; y: number }>;
		maxCol: number;
	} {
		const byColumn: Record<number, Capability[]> = {};
		for (const c of active) {
			(byColumn[c.column] ??= []).push(c);
		}
		const pos: Record<string, { x: number; y: number }> = {};
		pos['seed'] = { x: columnX(0), y: CENTER_Y };
		let maxCol = 1;
		for (const [col, caps] of Object.entries(byColumn)) {
			maxCol = Math.max(maxCol, Number(col));
			const n = caps.length;
			const blockTop = CENTER_Y - ((n - 1) * ROW_GAP) / 2;
			for (let i = 0; i < n; i++) {
				pos[nodeId(caps[i].id)] = { x: columnX(Number(col)), y: blockTop + i * ROW_GAP };
			}
		}
		// terminal recon node sits one column past the pipeline tail — OUTSIDE all
		// bands (depth band max column is 7; recon at maxCol+1 is always to its right).
		pos['recon'] = { x: columnX(maxCol + 1), y: CENTER_Y };
		return { pos, maxCol };
	}

	// ── CapNodeData builder ───────────────────────────────────────────────────────
	const SEVERITY_ALLOWED = new Set(['critical', 'high', 'medium', 'low']);

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function buildCapData(cap: Capability): any {
		const needsKey = (cap.needsKeyTools?.length ?? 0) > 0;

		let severityDots: ('critical' | 'high' | 'medium' | 'low')[] | undefined;
		if (cap.id === 'vuln-scan') {
			severityDots = (engine.depth.nuclei_severities ?? [])
				.filter((s) => SEVERITY_ALLOWED.has(s))
				.map((s) => s as 'critical' | 'high' | 'medium' | 'low');
		}

		let previewState: 'run' | 'skip-disabled' | 'skip-key' | null = null;
		if (previewMode) previewState = 'run';

		return {
			capId: cap.id,
			label: cap.label,
			producesNoun: cap.producesNoun,
			phase: cap.phase,
			required: cap.required,
			enabled: true,
			icon: cap.icon,
			needsKey,
			severityDots,
			previewState,
			onToggle: handleToggle,
			onConfigure: handleConfigure,
			onDelete: handleDelete
		};
	}

	// ── Edge dependency graph ─────────────────────────────────────────────────────
	// EVERY edge is a REAL node→node edge (source/target are real node ids), so the
	// wire auto-tracks node drags. There are NO anchor nodes. EXIT/ENTRY resolution
	// over the ACTIVE set guarantees each edge spans only ADJACENT occupied columns:
	// any disabled (empty) column between source and target is skipped, so no wire
	// ever pierces a node body (the no-pierce invariant).
	interface EdgeSpec {
		source: string; // capId or 'seed'
		target: string; // capId or 'recon'
		artifact: ArtifactType;
	}

	const SEED_TARGETS = ['dns-whois', 'related-domains', 'org-asn'];
	// Discovery EXIT preference (feeds the expansion entry). dns-whois is required/on.
	const DISCOVERY_EXIT_PREF = ['dns-whois', 'related-domains', 'org-asn'];
	// Expansion ENTRY preference (the node the discovery exit hands hosts to).
	const EXPANSION_ENTRY_PREF = ['subdomain-enum', 'cloud-recon'];
	// http-probe live-hosts fan: parallel col5 leaves (no wires between siblings).
	const LIVE_HOST_FAN = ['screenshot', 'url-discovery', 'dir-fuzz', 'param-vhost'];
	// Expansion EXIT preference (rightmost active expansion node feeds depth).
	const EXPANSION_EXIT_PREF = [
		'url-discovery',
		'dir-fuzz',
		'param-vhost',
		'screenshot',
		'http-probe',
		'port-scan',
		'subdomain-enum'
	];
	// Depth FINDING nodes (each lands on recon / reporting).
	const DEPTH_FINDINGS = ['vuln-scan', 'takeover-dns', 'js-secrets', 'tls-ssl'];

	function capPhase(capId: string): Phase | null {
		return CAPABILITIES.find((c) => c.id === capId)?.phase ?? null;
	}

	// First active id from a preference list (resolves an exit/entry from ACTIVE set).
	function firstActive(pref: string[], on: (id: string) => boolean): string | null {
		return pref.find(on) ?? null;
	}

	// Build the FULL real node→node edge list over the ACTIVE capabilities. Exit/entry
	// resolution skips disabled columns so every edge is Δcol ≥ 1 with no active node
	// strictly between source and target.
	function computeEdgeSpecs(activeIdList: string[]): EdgeSpec[] {
		const specs: EdgeSpec[] = [];
		const on = (id: string) => activeIdList.includes(id);
		const activeOf = (phase: Phase) => activeIdList.filter((id) => capPhase(id) === phase);

		// — seed → each active discovery cap —
		for (const t of SEED_TARGETS) {
			if (on(t)) specs.push({ source: 'seed', target: t, artifact: 'seed' });
		}

		// — DISCOVERY → EXPANSION: discoveryExit → expansionEntry (artifact "hosts") —
		const discoveryExit = firstActive(DISCOVERY_EXIT_PREF, on) ?? activeOf('discovery')[0] ?? null;
		const expansionEntry =
			firstActive(EXPANSION_ENTRY_PREF, on) ??
			activeIdList.find((id) => capPhase(id) === 'expansion') ??
			null;
		if (discoveryExit && expansionEntry) {
			specs.push({ source: discoveryExit, target: expansionEntry, artifact: 'hosts' });
		}

		// — EXPANSION internal mini-DAG —
		// subdomain-enum → port-scan
		if (on('subdomain-enum') && on('port-scan')) {
			specs.push({ source: 'subdomain-enum', target: 'port-scan', artifact: 'subdomains' });
		}
		// (port-scan if active else subdomain-enum) → http-probe
		if (on('http-probe')) {
			const liveSrc = on('port-scan') ? 'port-scan' : on('subdomain-enum') ? 'subdomain-enum' : null;
			if (liveSrc) {
				specs.push({
					source: liveSrc,
					target: 'http-probe',
					artifact: on('port-scan') ? 'ports' : 'subdomains'
				});
			}
		}
		// subdomain-enum → cloud-recon
		if (on('subdomain-enum') && on('cloud-recon')) {
			specs.push({ source: 'subdomain-enum', target: 'cloud-recon', artifact: 'subdomains' });
		}
		// http-probe → each active live-hosts fan leaf (Δcol = 1)
		if (on('http-probe')) {
			for (const t of LIVE_HOST_FAN) {
				if (on(t)) specs.push({ source: 'http-probe', target: t, artifact: 'live-hosts' });
			}
		}

		// — EXPANSION → DEPTH: expansionExit → each active depth finding ("attack surface") —
		const expansionExit = firstActive(EXPANSION_EXIT_PREF, on);
		const activeDepthFindings = DEPTH_FINDINGS.filter(on);
		if (expansionExit) {
			for (const t of activeDepthFindings) {
				specs.push({ source: expansionExit, target: t, artifact: 'live-hosts' });
			}
		}

		// — DEPTH internal: each active depth finding → reporting (artifact "findings") —
		if (on('reporting')) {
			for (const s of activeDepthFindings) {
				specs.push({ source: s, target: 'reporting', artifact: 'findings' });
			}
		}

		// — DEPTH → RECON (recon is the TARGET, so its incoming edge tracks the drag) —
		if (on('reporting')) {
			specs.push({ source: 'reporting', target: 'recon', artifact: 'report' });
		} else {
			for (const s of activeDepthFindings) {
				specs.push({ source: s, target: 'recon', artifact: 'findings' });
			}
		}

		return specs;
	}

	// ── Hover focus (lane-focus dimming) ────────────────────────────────────────
	let hoveredCapId = $state<string | null>(null);

	// Map a spec endpoint (capId | 'seed' | 'recon') to its real node id.
	function endpointNodeId(end: string): string {
		return end === 'seed' || end === 'recon' ? end : nodeId(end);
	}

	// Set of node ids to KEEP lit for the current hover (null = no hover, all lit).
	// Recomputed from the REAL node→node edges, so neighbours (including recon and
	// the inter-phase exits/entries) follow whatever the new edge graph wired up.
	function computeFocusIds(specs: EdgeSpec[], hovered: string | null): string[] | null {
		if (!hovered) return null;
		const self = nodeId(hovered);
		const keep: string[] = [self];
		for (const spec of specs) {
			const s = endpointNodeId(spec.source);
			const t = endpointNodeId(spec.target);
			if (s === self && !keep.includes(t)) keep.push(t);
			if (t === self && !keep.includes(s)) keep.push(s);
		}
		return keep;
	}

	// ── Node / edge builders (pure; positions injected by caller) ────────────────
	function buildNodes(
		active: Capability[],
		posFor: (id: string) => { x: number; y: number },
		focusIds: string[] | null
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
	): any[] {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const result: any[] = [];

		// Seed node.
		result.push({
			id: 'seed',
			type: 'seedCard',
			position: posFor('seed'),
			data: {},
			draggable: true,
			connectable: false,
			selectable: false
		});

		// Capability nodes.
		for (const cap of active) {
			const id = nodeId(cap.id);
			const dimmed = focusIds ? !focusIds.includes(id) : false;
			result.push({
				id,
				type: 'capabilityNode',
				position: posFor(id),
				data: buildCapData(cap),
				draggable: true,
				connectable: false,
				selectable: false,
				selected: cap.id === selectedCapabilityId,
				style: dimmed
					? 'opacity: 0.32; filter: saturate(0.6); transition: opacity .16s ease;'
					: 'transition: opacity .16s ease;'
			});
		}

		// Terminal recon-data node — mirror of seed, one column past the tail.
		const reconDimmed = focusIds ? !focusIds.includes('recon') : false;
		result.push({
			id: 'recon',
			type: 'reconData',
			position: posFor('recon'),
			data: { outputs: getReconOutputs(engine) },
			draggable: true,
			connectable: false,
			selectable: false,
			style: reconDimmed
				? 'opacity: 0.32; filter: saturate(0.6); transition: opacity .16s ease;'
				: 'transition: opacity .16s ease;'
		});

		return result;
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function buildEdges(
		specs: EdgeSpec[],
		focusIds: string[] | null
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
	): any[] {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const out: any[] = [];

		// Dedupe always-on labels: only the FIRST edge of each `${sourceId}|${artifact}`
		// key shows its label always (the data lineage once); the rest reveal on hover.
		// e.g. http-probe's "live hosts" fan and the expansion→depth "live hosts" fan
		// each label exactly once instead of stacking.
		const labelledKeys = new Set<string>();

		for (const spec of specs) {
			const sourceId = endpointNodeId(spec.source);
			const targetId = endpointNodeId(spec.target);

			const sPhase = spec.source === 'seed' ? 'discovery' : capPhase(spec.source);
			const tPhase = spec.target === 'recon' ? 'depth' : capPhase(spec.target);
			const crossPhase = sPhase !== tPhase;

			const key = `${sourceId}|${spec.artifact}`;
			const firstOfKey = !labelledKeys.has(key);
			if (firstOfKey) labelledKeys.add(key);

			let opacityMul = 1;
			if (focusIds) {
				opacityMul = focusIds.includes(sourceId) && focusIds.includes(targetId) ? 1 : 0.18;
			}

			out.push({
				id: `${sourceId}__${targetId}`,
				source: sourceId,
				target: targetId,
				type: 'artifact',
				data: {
					artifact: spec.artifact,
					label: ARTIFACT_LABEL[spec.artifact],
					crossPhase,
					// Labels are ALWAYS visible but deduped: first edge per source|artifact
					// shows always, siblings reveal on hover. Preview forces all labels on.
					alwaysLabel: previewMode || firstOfKey,
					showLabel: true,
					animated: previewMode
				},
				style: `opacity: ${opacityMul}; transition: opacity .16s ease;`,
				markerEnd: { type: MarkerType.ArrowClosed }
			});
		}

		return out;
	}

	// ── Reactive flow state (official pattern: $state.raw + bind:) ──────────────
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let nodes = $state.raw<any[]>([]);
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let edges = $state.raw<any[]>([]);

	// Tidy-up nonce: bumping it forces the next rebuild back to pure column layout.
	let tidyNonce = $state(0);
	let lastTidyNonce = 0;

	// Reconcile effect: rebuilds nodes/edges from engine + UI state, preserving
	// current drag positions. Depends on engine/previewMode/selection/hover/tidy.
	// Reads `nodes` via untrack so drag (which mutates `nodes` natively via bind:)
	// never re-triggers this effect → no reactive loop.
	$effect(() => {
		// Track the inputs that should drive a rebuild.
		void engine;
		void previewMode;
		void selectedCapabilityId;
		void hoveredCapId;
		void tidyNonce;

		const active = getActiveCapabilities(engine);
		const activeIdList = active.map((c) => c.id);
		const specs = computeEdgeSpecs(activeIdList);
		const focusIds = computeFocusIds(specs, hoveredCapId);

		const { pos: layout } = computeLayout(active);
		const forceLayout = tidyNonce !== lastTidyNonce;
		lastTidyNonce = tidyNonce;

		// Preserve existing positions (cap/seed/recon) unless tidy-up reset.
		const prev: Record<string, { x: number; y: number }> = {};
		if (!forceLayout) {
			for (const n of untrack(() => nodes)) {
				prev[n.id] = n.position;
			}
		}
		const posFor = (id: string) => prev[id] ?? layout[id] ?? { x: 0, y: CENTER_Y };

		nodes = buildNodes(active, posFor, focusIds);
		edges = buildEdges(specs, focusIds);
	});

	// ── Phase bands (tall neutral swim columns, rendered in flow coords) ─────────
	// Derived from current node positions so the band tracks dragged nodes.
	interface Band {
		phase: Phase;
		num: number;
		title: string;
		accent: string;
		activeCount: number;
		totalCount: number;
		empty: boolean;
		x: number; // left edge of the band
		width: number; // band width across the phase columns
		top: number; // band top (flow coords)
		height: number; // band height
	}

	let active = $derived(getActiveCapabilities(engine));

	// Vertical extent of the CAPABILITY nodes only → a single shared band height,
	// centered on their span. Seed and recon are excluded, so dragging them
	// (especially the terminal recon node, which sits OUTSIDE the bands) never
	// resizes the phase containers.
	let bandBox = $derived.by<{ top: number; height: number }>(() => {
		let minY = CENTER_Y;
		let maxY = CENTER_Y + NODE_H;
		for (const n of nodes) {
			if (n.type !== 'capabilityNode') continue;
			if (n.position.y < minY) minY = n.position.y;
			if (n.position.y + NODE_H > maxY) maxY = n.position.y + NODE_H;
		}
		const span = maxY - minY;
		const height = Math.max(span + BAND_SPAN_PAD, BAND_MIN_HEIGHT);
		// center the band on the node span's center so single-node columns stay full-height
		const spanCenter = (minY + maxY) / 2;
		const top = spanCenter - height / 2;
		return { top, height };
	});

	let bands = $derived.by<Band[]>(() => {
		const out: Band[] = [];
		PHASE_ORDER.forEach((phase) => {
			const range = PHASE_COLUMN_RANGE[phase];
			const c = phaseCounts(active, phase);
			const rawX = columnX(range.min) - PAD;
			const rawWidth = (range.max - range.min) * COL_GAP + NODE_W + 2 * PAD;
			// shrink each band by a gutter so adjacent bands read as separate columns
			const x = rawX + BAND_GUTTER / 2;
			const width = rawWidth - BAND_GUTTER;
			out.push({
				phase,
				num: PHASE_NUM[phase],
				title: PHASE_TITLE[phase],
				accent: PHASE_COLORS[phase].accent,
				activeCount: c.active,
				totalCount: c.total,
				empty: c.active === 0,
				x,
				width,
				top: bandBox.top,
				height: bandBox.height
			});
		});
		return out;
	});

	// ── Handlers ───────────────────────────────────────────────────────────────────
	function handleToggle(capId: string, enabled: boolean) {
		const cap = CAPABILITIES.find((c) => c.id === capId);
		if (!cap || cap.required) return;
		if (!enabled) onEngineChange?.(applyDisableCapability(engine, capId));
		else onEngineChange?.(applyEnableCapability(engine, capId));
	}

	function handleConfigure(capId: string) {
		onCapabilitySelected?.(capId);
	}

	function handleDelete(capId: string) {
		const cap = CAPABILITIES.find((c) => c.id === capId);
		if (!cap || cap.required) return;
		if (selectedCapabilityId === capId) onCapabilitySelected?.(null);
		onEngineChange?.(applyDisableCapability(engine, capId));
	}

	// ── Tidy up (snap nodes back to computed layout + re-fit) ───────────────────
	let fitNonce = $state(0);
	function tidyUp() {
		tidyNonce++;
		fitNonce++;
	}

	// ── Add-step palette ──────────────────────────────────────────────────────────
	let showAddPalette = $state(false);
	let addPhase = $state<Phase | null>(null);

	function openPalette(phase: Phase | null) {
		addPhase = phase;
		showAddPalette = true;
	}

	function handleAdd(capId: string) {
		onEngineChange?.(applyEnableCapability(engine, capId));
		showAddPalette = false;
	}

	function closePalette() {
		showAddPalette = false;
	}

	// Topbar "+ Add Step": opens the all-phases palette when the nonce increments.
	let lastAddNonce = $state(0);
	$effect(() => {
		if (requestAddOpen !== lastAddNonce) {
			lastAddNonce = requestAddOpen;
			if (requestAddOpen > 0) openPalette(null);
		}
	});

	// ── Node hover wiring ────────────────────────────────────────────────────────
	function onNodePointerEnter({ node }: { node: { id: string } }) {
		if (node.id.startsWith('cap-')) hoveredCapId = node.id.slice('cap-'.length);
	}
	function onNodePointerLeave() {
		hoveredCapId = null;
	}
</script>

<div class="canvas-wrap">
	<SvelteFlowProvider>
		<EngineFlow
			bind:nodes
			bind:edges
			{nodeTypes}
			{edgeTypes}
			fitKey={active.length}
			{fitNonce}
			{onNodePointerEnter}
			{onNodePointerLeave}
		>
			<!-- Phase bands: live in flow coords (pan/zoom) but BEHIND the wires.
			     Neutral gray swim columns — NOT phase-colored fills. Pointer-events
			     are off except the header "Add step" / empty-phase ghost buttons. -->
			<ViewportPortal target="back">
				<div class="band-layer">
					{#each bands as b (b.phase)}
						<div
							class="phase-band"
							style="left: {b.x}px; top: {b.top}px; width: {b.width}px; height: {b.height}px; --accent: {b.accent};"
						>
							<span class="band-accent-line" aria-hidden="true"></span>

							<!-- Header pinned to the top of the band -->
							<div class="band-header">
								<span class="phase-num">{b.num}</span>
								<span class="phase-title">{b.title}</span>
								<span class="phase-count">{b.activeCount}/{b.totalCount} on</span>
								<span class="band-spacer"></span>
								<Button
									variant="ghost"
									size="sm"
									class="band-add"
									onclick={() => openPalette(b.phase)}
								>
									<Plus size={13} />
									Add step
								</Button>
							</div>

							<!-- Empty-phase ghost: structure never collapses -->
							{#if b.empty}
								<div class="band-empty">
									<Button
										variant="ghost"
										size="sm"
										class="empty-ghost"
										onclick={() => openPalette(b.phase)}
									>
										<Plus size={14} />
										Add your first step
									</Button>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</ViewportPortal>
		</EngineFlow>
	</SvelteFlowProvider>

	<!-- Top-right overlay (above flow): preview indicator + Tidy up -->
	<div class="tidy-overlay">
		{#if previewMode}
			<span class="preview-pill">
				<span class="preview-dot"></span>
				Execution preview
			</span>
		{/if}
		<Button variant="secondary" size="sm" onclick={tidyUp} title="Tidy up layout">
			<Wand2 size={14} />
			Tidy up
		</Button>
	</div>

	<AddStepPalette
		open={showAddPalette}
		phase={addPhase}
		{engine}
		onAdd={handleAdd}
		onClose={closePalette}
	/>
</div>

<style>
	.canvas-wrap {
		width: 100%;
		height: 100%;
		position: relative;
		overflow: hidden;
	}

	/* ── Top-right overlay (preview pill + Tidy up) ── */
	.tidy-overlay {
		position: absolute;
		top: 12px;
		right: 12px;
		z-index: 5;
		display: flex;
		align-items: center;
		gap: 8px;
		pointer-events: auto;
	}

	.preview-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 26px;
		padding: 0 10px;
		border-radius: 9999px;
		background: var(--muted);
		border: 1px solid var(--border);
		font-size: 11px;
		font-weight: 500;
		color: var(--muted-foreground);
		white-space: nowrap;
	}
	.preview-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--muted-foreground);
		animation: preview-blink 1.4s ease-in-out infinite;
	}
	@keyframes preview-blink {
		0%,
		100% {
			opacity: 0.35;
		}
		50% {
			opacity: 1;
		}
	}

	/* ── Phase band layer (rendered into .svelte-flow__viewport-back) ──
	   Sits BEHIND the edges (which come later in viewport DOM order). The layer
	   ignores pointer events; only the header / ghost buttons opt back in. */
	.band-layer {
		position: absolute;
		top: 0;
		left: 0;
		z-index: 0;
		pointer-events: none;
	}

	/* Tall NEUTRAL swim column — gray, not phase-colored, not pastel. */
	.phase-band {
		position: absolute;
		border-radius: 1rem; /* rounded-2xl */
		border: 1px solid var(--border);
		background: color-mix(in oklch, var(--muted) 45%, var(--background));
		overflow: hidden;
	}
	:global(.dark) .phase-band {
		background: color-mix(in oklch, var(--card) 55%, var(--background));
	}

	/* subtle 2px accent line at the very top of the band */
	.band-accent-line {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: var(--accent);
		opacity: 0.85;
		pointer-events: none;
	}

	.band-header {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 12px 0 14px;
		pointer-events: none;
	}
	.band-spacer {
		flex: 1;
	}

	.phase-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		border-radius: 5px;
		font-size: 11px;
		font-weight: 700;
		color: #fff;
		background: var(--accent);
		flex-shrink: 0;
	}

	.phase-title {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--foreground);
		flex-shrink: 0;
	}

	.phase-count {
		font-size: 10px;
		font-weight: 600;
		color: var(--muted-foreground);
		flex-shrink: 0;
	}

	.phase-band :global(.band-add) {
		height: 24px;
		padding: 0 8px;
		font-size: 11px;
		color: var(--muted-foreground);
		pointer-events: auto;
	}
	.phase-band :global(.band-add:hover) {
		color: var(--foreground);
	}

	/* empty-phase ghost — centered dashed call-to-action */
	.band-empty {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		pointer-events: none;
	}
	.phase-band :global(.empty-ghost) {
		height: auto;
		padding: 10px 16px;
		border: 1px dashed var(--border);
		border-radius: 0.625rem;
		font-size: 12px;
		font-weight: 500;
		color: var(--muted-foreground);
		background: transparent;
		pointer-events: auto;
	}
	.phase-band :global(.empty-ghost:hover) {
		color: var(--foreground);
		border-color: color-mix(in oklch, var(--ring) 50%, transparent);
		background: color-mix(in oklch, var(--muted) 50%, transparent);
	}

	/* ── SvelteFlow overrides not covered by --xy-* vars ── */
	:global(.svelte-flow) {
		background: transparent !important;
	}

	:global(.svelte-flow .svelte-flow__node:focus) {
		outline: none;
	}

	/* Guarantee the wires render ABOVE the back portal band layer. The viewport
	   children are stacked by DOM order (back → edges → nodes); these explicit
	   z-indexes make the intent unambiguous and survive any stacking context.
	   Verified correct — wires must stay BEHIND node cards. */
	:global(.svelte-flow__viewport-back) {
		z-index: 0;
	}
	:global(.svelte-flow__edges) {
		z-index: 2;
	}
	:global(.svelte-flow__edge) {
		z-index: 2;
	}

	:global(.svelte-flow__controls) {
		border-radius: 8px !important;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12) !important;
		overflow: hidden;
	}

	:global(.svelte-flow__controls-button) {
		width: 28px !important;
		height: 28px !important;
	}

	:global(.svelte-flow__controls-button:last-child) {
		border-bottom: none !important;
	}

	:global(.svelte-flow__controls-button:hover) {
		background: var(--accent) !important;
		color: var(--accent-foreground) !important;
	}

	:global(.svelte-flow__controls-button svg) {
		fill: currentColor !important;
		stroke: currentColor !important;
	}

	:global(.svelte-flow__edge-path) {
		stroke-linecap: round;
	}
</style>
