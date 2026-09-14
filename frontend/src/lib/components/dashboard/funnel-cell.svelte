<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { FUNNEL_DROP, FunnelStep } from '$lib/config/dashboard';
	import { windowDays, type DashboardFunnel, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		funnel: DashboardFunnel;
		window: DashboardWindow;
		class?: string;
	}

	let { funnel, window, class: className = '' }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const W = 640;
	const H = 150;
	const PAD = 8;

	let steps = $derived(funnel.steps);
	let max = $derived(Math.max(1, steps[0]?.count ?? 1));
	let days = $derived(windowDays(window));
	let sw = $derived(W / Math.max(1, steps.length));
	let ph = H - 2 * PAD;
	const hh = (v: number) => Math.max(5, Math.sqrt(v / max) * ph);
	let hovered = $state<string | null>(null);

	let bands = $derived(
		steps.slice(0, -1).map((s, i) => {
			const next = steps[i + 1];
			const h0 = hh(s.count);
			const h1 = hh(next.count);
			const x0 = i * sw + sw * 0.5;
			const x1 = (i + 1) * sw + sw * 0.5;
			const cy = PAD + ph / 2;
			const last = i === steps.length - 2;
			return {
				key: s.key,
				next: next.key,
				d: `M${x0} ${cy - h0 / 2} C ${x0 + sw * 0.45} ${cy - h0 / 2}, ${x1 - sw * 0.45} ${cy - h1 / 2}, ${x1} ${cy - h1 / 2} L${x1} ${cy + h1 / 2} C ${x1 - sw * 0.45} ${cy + h1 / 2}, ${x0 + sw * 0.45} ${cy + h0 / 2}, ${x0} ${cy + h0 / 2} Z`,
				fill: last ? 'var(--destructive)' : 'var(--series)',
				opacity: last ? 0.7 : 0.14 + i * 0.13,
				drop: Math.max(0, s.count - next.count),
				dropLabel: FUNNEL_DROP[s.key]
			};
		})
	);
	let posts = $derived(
		steps.map((s, i) => ({
			key: s.key,
			x: i * sw + sw * 0.5,
			h: hh(s.count),
			fill: s.key === FunnelStep.Findings ? 'var(--destructive)' : 'var(--series)'
		}))
	);

	function href(step: (typeof steps)[number]): string {
		const spec = SURFACE[(step.tab ?? SurfaceDimension.WEB_ASSETS) as SurfaceDimension] ?? WEB;
		if (!step.query) return ROUTES.surface(spec.tab);
		return ROUTES.surface(spec.tab, { [spec.queryParam]: step.query });
	}
	const share = (i: number) =>
		i === 0 || !steps[i - 1].count ? null : Math.round((steps[i].count / steps[i - 1].count) * 100);
	const hint = (i: number) => {
		const s = steps[i];
		const parts = [`${s.count.toLocaleString()} ${s.label.toLowerCase()}`];
		const pct = share(i);
		if (pct !== null) parts.push(`${pct}% of ${steps[i - 1].label.toLowerCase()}`);
		parts.push(s.query === null ? 'Opens coverage' : `Opens ${s.query || WEB.label}`);
		return parts.join(' · ');
	};
	const lit = (key: string) => !hovered || hovered === key;
	const bandLit = (b: { key: string; next: string }) =>
		!hovered || hovered === b.key || hovered === b.next;
</script>

<Cell
	id="funnel"
	title="Attack surface funnel"
	href={ROUTES.surface(WEB.tab)}
	hrefLabel={WEB.label}
	class={className}
>
	<div class="grid grid-cols-5 gap-1">
		{#each steps as s, i (s.key)}
			<Hint text={hint(i)}>
				{#snippet child(props)}
					<a
						{...props}
						href={href(s)}
						class="flex min-w-0 flex-col items-center gap-0.5 rounded-md px-1 py-1.5 text-center transition-colors hover:bg-muted/50"
						onmouseenter={() => (hovered = s.key)}
						onmouseleave={() => (hovered = null)}
						onfocus={() => (hovered = s.key)}
						onblur={() => (hovered = null)}
					>
						<span
							class="text-base leading-none font-semibold tracking-tight tabular-nums sm:text-xl {s.key ===
							FunnelStep.Findings
								? 'text-destructive'
								: ''}"
						>
							{s.count.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground">
							{s.label}{#if share(i) !== null}<span class="text-2xs"> · {share(i)}%</span>{/if}
						</span>
						<span class="h-4 text-2xs text-info tabular-nums">
							{#if s.new_in_window !== null && s.new_in_window > 0}▲ {s.new_in_window.toLocaleString()}
								in {days}d{/if}
						</span>
					</a>
				{/snippet}
			</Hint>
		{/each}
	</div>
	<svg viewBox="0 0 {W} {H}" class="h-[150px] w-full" preserveAspectRatio="none" aria-hidden="true">
		{#each bands as b (b.key)}
			<path
				d={b.d}
				fill={b.fill}
				opacity={bandLit(b) ? b.opacity : b.opacity * 0.3}
				class="transition-opacity duration-200"
			/>
		{/each}
		{#each posts as p (p.key)}
			<rect
				x={p.x - 3.5}
				y={PAD + ph / 2 - p.h / 2}
				width="7"
				height={p.h}
				rx="2.5"
				fill={p.fill}
				opacity={lit(p.key) ? 1 : 0.35}
				class="transition-opacity duration-200"
			/>
		{/each}
	</svg>
	<div class="grid grid-cols-10 text-center text-2xs text-muted-foreground tabular-nums">
		{#each bands as b, i (b.key)}
			<span
				class="col-span-2 transition-opacity duration-200 {i === 0 ? 'col-start-2' : ''} {bandLit(b)
					? ''
					: 'opacity-40'}"
			>
				{b.drop.toLocaleString()}
				{b.dropLabel}
			</span>
		{/each}
	</div>
	<div class="grid grid-cols-5 text-center font-mono text-2xs text-muted-foreground">
		{#each steps as s (s.key)}
			<span class="truncate transition-opacity duration-200 {lit(s.key) ? '' : 'opacity-40'}">
				{s.query === null ? 'coverage' : s.query || 'all'}
			</span>
		{/each}
	</div>
</Cell>
