<script lang="ts" module>
	import CapabilityNode from './capability-node.svelte';
	import SeedNode from './seed-node.svelte';
	import ReconNode from './recon-node.svelte';
	import GutterAnchor from './gutter-anchor.svelte';
	import ArtifactEdge from './artifact-edge.svelte';

	// Created ONCE at module scope — recreating per render triggers the
	// "new nodeTypes object" warning from SvelteFlow.
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const nodeTypes: any = {
		capabilityNode: CapabilityNode,
		seedCard: SeedNode,
		reconData: ReconNode,
		gutterAnchor: GutterAnchor
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
	const COL_GAP = 340;
	const NODE_W = 264;
	const NODE_H = 92;
	const ROW_GAP = 180;
	const CENTER_Y = 400;
	const PAD = 40;
	// minimum tall-band height + extra vertical breathing around the node span
	const BAND_MIN_HEIGHT = 430;
	const BAND_SPAN_PAD = 170;
	// gutter taken out of each band so adjacent bands read as separate columns
	const BAND_GUTTER = 28;

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
	interface EdgeSpec {
		source: string; // capId or 'seed'
		target: string; // capId
		artifact: ArtifactType;
	}

	const SEED_TARGETS = ['dns-whois', 'related-domains', 'org-asn'];
	// Discovery "spine" feeding the expansion chain (dns-whois is required/on).
	const DISCOVERY_SPINE = ['dns-whois', 'related-domains', 'org-asn'];
	// col5 expansion fan-out fed by http-probe (parallel siblings, no wires between).
	const EXPANSION_LEAVES = ['screenshot', 'url-discovery', 'dir-fuzz', 'param-vhost'];

	function capPhase(capId: string): Phase | null {
		return CAPABILITIES.find((c) => c.id === capId)?.phase ?? null;
	}
	function capProduces(capId: string): ArtifactType {
		return CAPABILITIES.find((c) => c.id === capId)?.produces ?? 'seed';
	}

	// Build INTRA-PHASE edges following the dependency chain over ACTIVE nodes.
	// Each edge hops from the nearest active upstream to the next active downstream
	// so any disabled (empty) column in between is simply skipped — the wire only
	// crosses EMPTY columns and therefore never passes through a node body.
	function computeEdgeSpecs(activeIdList: string[]): EdgeSpec[] {
		const specs: EdgeSpec[] = [];
		const on = (id: string) => activeIdList.includes(id);

		// — DISCOVERY (col1): seed → each active discovery node (parallel) —
		for (const t of SEED_TARGETS) {
			if (on(t)) specs.push({ source: 'seed', target: t, artifact: 'seed' });
		}

		// First active discovery node = the spine head feeding expansion.
		const spineHead = DISCOVERY_SPINE.find((id) => on(id)) ?? null;

		// — EXPANSION chain (left → right mini-DAG over active nodes) —
		// spine → subdomain-enum (col1 → col2)
		if (on('subdomain-enum') && spineHead) {
			specs.push({
				source: spineHead,
				target: 'subdomain-enum',
				artifact: capProduces(spineHead)
			});
		}
		// cloud-recon: col2 parallel sibling fed by subdomain-enum if active else the
		// discovery spine. No downstream consumer.
		if (on('cloud-recon')) {
			const src = on('subdomain-enum') ? 'subdomain-enum' : spineHead;
			if (src) specs.push({ source: src, target: 'cloud-recon', artifact: capProduces(src) });
		}

		// subdomain-enum → port-scan (col2 → col3)
		if (on('subdomain-enum') && on('port-scan')) {
			specs.push({ source: 'subdomain-enum', target: 'port-scan', artifact: 'subdomains' });
		}

		// live-host producer (port-scan if active, else subdomain-enum) → http-probe.
		// If port-scan is off its col3 is empty, so subdomain-enum (col2) → http-probe
		// (col4) only crosses the empty col3.
		if (on('http-probe')) {
			const liveSrc = on('port-scan') ? 'port-scan' : on('subdomain-enum') ? 'subdomain-enum' : null;
			if (liveSrc) {
				specs.push({
					source: liveSrc,
					target: 'http-probe',
					artifact: capProduces(liveSrc)
				});
			}
		}

		// http-probe → EACH active col5 sibling (parallel fan-out, Δcol = 1).
		if (on('http-probe')) {
			for (const t of EXPANSION_LEAVES) {
				if (on(t)) specs.push({ source: 'http-probe', target: t, artifact: 'live-hosts' });
			}
		}

		// — DEPTH: parallel terminal siblings. NO node-to-node wires within depth and
		// NO individual long wires to recon. Aggregation is conveyed by the box arrow
		// (Depth band → Recon Data) added separately as an inter-phase connector. —

		return specs;
	}

	// ── Hover focus (lane-focus dimming) ────────────────────────────────────────
	let hoveredCapId = $state<string | null>(null);

	// Set of node ids to KEEP lit for the current hover (null = no hover, all lit).
	function computeFocusIds(specs: EdgeSpec[], hovered: string | null): string[] | null {
		if (!hovered) return null;
		const self = nodeId(hovered);
		const keep: string[] = [self, 'seed'];
		for (const spec of specs) {
			const s = spec.source === 'seed' ? 'seed' : nodeId(spec.source);
			const t = nodeId(spec.target);
			if (s === self && !keep.includes(t)) keep.push(t);
			if (t === self && !keep.includes(s)) keep.push(s);
		}
		// A hovered depth node keeps the terminal recon node lit (depth aggregates → recon).
		if (capPhase(hovered) === 'depth' && !keep.includes('recon')) keep.push('recon');
		return keep;
	}

	// ── Inter-phase connectors (box arrows in the empty gutters between bands) ───
	// Implemented as INVISIBLE anchor nodes at each band's right-center / the next
	// band's left-center, joined by a heavier artifact edge with a label chip. The
	// anchors live in the 40px gutters where there are NO nodes, so the connector
	// can never pierce a node body.
	interface ConnectorSpec {
		id: string;
		fromX: number;
		toX: number;
		label: string;
		artifact: ArtifactType;
	}

	// Returns the x-geometry of a phase band (mirrors the `bands` derived below).
	function bandGeometry(phase: Phase): { left: number; right: number } {
		const range = PHASE_COLUMN_RANGE[phase];
		const rawX = columnX(range.min) - PAD;
		const rawWidth = (range.max - range.min) * COL_GAP + NODE_W + 2 * PAD;
		const left = rawX + BAND_GUTTER / 2;
		const right = left + (rawWidth - BAND_GUTTER);
		return { left, right };
	}

	function computeConnectors(activeIdList: string[], reconX: number): ConnectorSpec[] {
		const out: ConnectorSpec[] = [];
		const hasPhase = (phase: Phase) =>
			activeIdList.some((id) => capPhase(id) === phase);

		const disc = bandGeometry('discovery');
		const exp = bandGeometry('expansion');
		const dep = bandGeometry('depth');

		// Discovery band → Expansion band
		if (hasPhase('discovery') && hasPhase('expansion')) {
			out.push({
				id: 'conn-disc-exp',
				fromX: disc.right,
				toX: exp.left,
				label: 'in-scope assets',
				artifact: 'hosts'
			});
		}
		// Expansion band → Depth band
		if (hasPhase('expansion') && hasPhase('depth')) {
			out.push({
				id: 'conn-exp-dep',
				fromX: exp.right,
				toX: dep.left,
				label: 'attack surface',
				artifact: 'live-hosts'
			});
		}
		// Depth band → Recon Data
		if (hasPhase('depth')) {
			out.push({
				id: 'conn-dep-recon',
				fromX: dep.right,
				toX: reconX,
				label: 'findings',
				artifact: 'findings'
			});
		}
		return out;
	}

	// ── Node / edge builders (pure; positions injected by caller) ────────────────
	function buildNodes(
		active: Capability[],
		posFor: (id: string) => { x: number; y: number },
		focusIds: string[] | null,
		connectors: ConnectorSpec[],
		bandCenterY: number
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

		// Invisible inter-phase gutter anchors (one source-end + one target-end per
		// connector). Positioned on the band edges at the shared band vertical center.
		for (const c of connectors) {
			result.push({
				id: `${c.id}-from`,
				type: 'gutterAnchor',
				position: { x: c.fromX, y: bandCenterY },
				data: {},
				draggable: false,
				connectable: false,
				selectable: false
			});
			result.push({
				id: `${c.id}-to`,
				type: 'gutterAnchor',
				position: { x: c.toX, y: bandCenterY },
				data: {},
				draggable: false,
				connectable: false,
				selectable: false
			});
		}

		return result;
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function buildEdges(
		specs: EdgeSpec[],
		connectors: ConnectorSpec[],
		focusIds: string[] | null
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
	): any[] {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const out: any[] = [];

		// — INTRA-PHASE edges (node-to-node, within a band) —
		for (const spec of specs) {
			const sourceId = spec.source === 'seed' ? 'seed' : nodeId(spec.source);
			const targetId = nodeId(spec.target);

			const sPhase = spec.source === 'seed' ? 'discovery' : capPhase(spec.source);
			const tPhase = capPhase(spec.target);
			const crossPhase = sPhase !== tPhase;

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
					showLabel: crossPhase || previewMode,
					animated: previewMode
				},
				style: `opacity: ${opacityMul}; transition: opacity .16s ease;`,
				markerEnd: { type: MarkerType.ArrowClosed }
			});
		}

		// — INTER-PHASE connectors (heavier box arrows in the gutters) —
		for (const c of connectors) {
			let opacityMul = 1;
			if (focusIds) {
				// Light a connector only when the recon terminal is in focus (depth hover)
				// — otherwise keep the prominent connectors calm during lane focus.
				const isReconConn = c.id === 'conn-dep-recon';
				opacityMul = isReconConn && focusIds.includes('recon') ? 1 : 0.18;
			}
			out.push({
				id: `edge-${c.id}`,
				source: `${c.id}-from`,
				target: `${c.id}-to`,
				type: 'artifact',
				data: {
					artifact: c.artifact,
					label: c.label,
					// crossPhase = heavier stroke + always-visible label chip.
					crossPhase: true,
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

		const { pos: layout, maxCol } = computeLayout(active);
		const forceLayout = tidyNonce !== lastTidyNonce;
		lastTidyNonce = tidyNonce;

		// Preserve existing positions (cap/seed/recon only) unless tidy-up reset.
		const prev: Record<string, { x: number; y: number }> = {};
		if (!forceLayout) {
			for (const n of untrack(() => nodes)) {
				if (n.type !== 'gutterAnchor') prev[n.id] = n.position;
			}
		}
		const posFor = (id: string) => prev[id] ?? layout[id] ?? { x: 0, y: CENTER_Y };

		// Shared band vertical center from the cap/seed/recon span (anchors excluded,
		// so they can never feed back into this geometry). Mirrors bandBox below.
		let minY = CENTER_Y;
		let maxY = CENTER_Y + NODE_H;
		for (const cap of active) {
			const p = posFor(nodeId(cap.id));
			if (p.y < minY) minY = p.y;
			if (p.y + NODE_H > maxY) maxY = p.y + NODE_H;
		}
		const seedP = posFor('seed');
		if (seedP.y < minY) minY = seedP.y;
		if (seedP.y + NODE_H > maxY) maxY = seedP.y + NODE_H;
		const bandCenterY = (minY + maxY) / 2;

		const reconX = layout['recon']?.x ?? columnX(maxCol + 1);
		const connectors = computeConnectors(activeIdList, posFor('recon').x ?? reconX);

		nodes = buildNodes(active, posFor, focusIds, connectors, bandCenterY);
		edges = buildEdges(specs, connectors, focusIds);
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

	// Vertical extent of all NON-ANCHOR nodes → a single shared band height,
	// centered on the node span. Anchors are excluded (they sit ON the band edges,
	// so including them would create a geometry feedback loop).
	let bandBox = $derived.by<{ top: number; height: number }>(() => {
		let minY = CENTER_Y;
		let maxY = CENTER_Y + NODE_H;
		for (const n of nodes) {
			if (n.type === 'gutterAnchor') continue;
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
