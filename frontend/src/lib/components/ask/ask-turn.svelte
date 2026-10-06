<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Brain from '@lucide/svelte/icons/brain';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { plainAnswer } from '$lib/components/scans/results/vulnerabilities/ask/answer-text';
	import AnswerLead from './answer-lead.svelte';
	import BlockCard from './block-card.svelte';
	import ReadAs from './read-as.svelte';
	import WorkLine, { type FunnelStep } from './work-line.svelte';
	import { causeLine, leadNumber } from './lead';
	import { BlockKind } from '$lib/config/ask';
	import { surfaceSpec } from '$lib/config/surface';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import type {
		AnswerBlock,
		AskMessage,
		AskTraceStep,
		BlockData,
		PinnedQuery
	} from '$lib/types/ask';

	interface Props {
		id?: string;
		folded?: boolean;
		onUnfold?: () => void;
		question: string;
		aboutLabel: string | null;
		intelligent: boolean;
		answer?: AskMessage | null;
		draft?: { text: string; trace: AskTraceStep[]; blocks: AnswerBlock[] } | null;
		datas: Map<string, BlockData>;
		threadId: string | null;
		filtered: boolean;
		scopeLabel: string | null;
		targets: number;
		focused: string | null;
		known: Set<string>;
		busy: boolean;
		offline: boolean;
		onAbout: (about: string, label: string) => void;
		onRef: (id: string) => void;
		onBlockChange: (block: AnswerBlock, data: BlockData, threadId: string) => void;
		onPin: (text: string, pinned: PinnedQuery, about: string) => void;
	}

	let {
		id,
		folded = false,
		onUnfold,
		question,
		aboutLabel,
		intelligent,
		answer = null,
		draft = null,
		datas,
		threadId,
		filtered,
		scopeLabel,
		targets,
		focused,
		known,
		busy,
		offline,
		onAbout,
		onRef,
		onBlockChange,
		onPin
	}: Props = $props();

	let blocks = $derived(answer?.blocks ?? draft?.blocks ?? []);
	let text = $derived(answer?.text ?? draft?.text ?? '');
	let trace = $derived(answer?.trace ?? draft?.trace ?? []);
	let working = $derived(!!draft && !text && !blocks.length);
	let lead = $derived(blocks.find((b) => b.kind !== BlockKind.CVE) ?? null);
	let summary = $derived.by(() => {
		const d = lead ? datas.get(lead.id) : undefined;
		const total = d?.error ? null : (d?.total ?? lead?.total ?? null);
		const capped = d?.capped ?? lead?.capped ?? false;
		const title = lead ? lead.title || noun(lead.dimension, total) : '';
		const first = plainAnswer(text).split(/(?<=[.!?])\s/, 1)[0] ?? '';
		return {
			count: total == null ? '' : `${total.toLocaleString()}${capped ? '+' : ''}`,
			line:
				total == null
					? first
					: [title, causeLine(d?.causes, total, capped)].filter(Boolean).join(' · ')
		};
	});
	let leadData = $derived(lead ? datas.get(lead.id) : undefined);

	function noun(dimension: string | null, count: number | null | undefined): string {
		const spec = surfaceSpec(dimension ?? '');
		return (count === 1 ? spec?.noun : spec?.nounPlural) ?? 'rows';
	}

	let funnel = $derived.by<FunnelStep[]>(() => {
		const d = leadData;
		const total = d?.error ? null : (d?.total ?? lead?.total);
		if (!lead || total == null) return [];
		const out: FunnelStep[] = [];
		if (d?.scope_total != null && d.scope_total !== total) {
			out.push({
				count: d.scope_total,
				capped: d.scope_capped,
				label: noun(lead.dimension, d.scope_total)
			});
		}
		out.push({
			count: total,
			capped: d?.capped ?? lead.capped,
			label: lead.title || noun(lead.dimension, total)
		});
		if (d?.causes?.groups.length) {
			out.push({
				count: d.causes.total_groups,
				label: d.causes.total_groups === 1 ? d.causes.one : d.causes.many
			});
		}
		return out;
	});

	let unscanned = $derived.by(() => {
		const seen: string[] = [];
		const lines: string[] = [];
		for (const b of blocks) {
			const d = datas.get(b.id);
			if (!b.dimension || seen.includes(b.dimension) || d?.covered == null) continue;
			seen.push(b.dimension);
			const missing = targets - d.covered;
			if (missing <= 0) continue;
			const label = surfaceSpec(b.dimension)?.label ?? b.dimension;
			lines.push(
				targets === 1
					? `${label} not scanned`
					: `${label} not scanned on ${missing} of ${targets} targets`
			);
		}
		return lines.join(' · ');
	});

	async function copy() {
		if (!answer) return;
		const text = plainAnswer(answer.text);
		const head = lead
			? funnel.find((f) => f.label === (lead.title || noun(lead.dimension, f.count)))
			: null;
		const headline = head
			? `${head.count.toLocaleString()}${head.capped ? '+' : ''} ${head.label}`
			: '';
		const lines = headline && !leadNumber(text, head?.count) ? [headline, text] : [text];
		if (await writeClipboard(lines.join('\n'))) toast.success('Copied');
	}
</script>

{#snippet bubble()}
	<div class={['flex flex-col items-end gap-1', draft && 'ask-rise']}>
		<div
			class="max-w-[85%] rounded-2xl rounded-br-md bg-muted px-4 py-2.5 text-sm leading-6 whitespace-pre-wrap wrap-anywhere sm:max-w-[75%]"
		>
			{#if aboutLabel}
				<span class="mb-0.5 flex items-center gap-1 text-2xs text-muted-foreground">
					<Sparkles class="size-3 text-primary" />
					About {aboutLabel}
				</span>
			{/if}
			{question}
		</div>
		{#if intelligent}
			<span class="inline-flex items-center gap-1 pr-1 text-2xs text-primary">
				<Brain class="size-3" />
				Intelligent
			</span>
		{/if}
	</div>
{/snippet}

{#if folded}
	<article class="flex flex-col gap-3">
		{@render bubble()}
		<div class="flex gap-3">
			<span
				class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
				aria-hidden="true"
			>
				<Sparkles class="size-3.5" />
			</span>
			<button
				type="button"
				class="flex min-w-0 flex-1 items-center gap-3 rounded-lg border bg-card/60 px-3 py-2 text-left hover:bg-muted/50"
				aria-expanded="false"
				aria-label="Show answer: {summary.count ? `${summary.count} ` : ''}{summary.line}"
				onclick={() => onUnfold?.()}
			>
				{#if summary.count}
					<span class="shrink-0 text-lg font-semibold tracking-tight tabular-nums"
						>{summary.count}</span
					>
				{/if}
				<span class="min-w-0 flex-1 truncate text-sm">{summary.line}</span>
				<ChevronDown class="size-4 shrink-0 text-muted-foreground" />
			</button>
		</div>
	</article>
{:else}
	<article
		id={id ? `turn-${id}` : undefined}
		tabindex="-1"
		class="flex flex-col gap-5 outline-none"
	>
		{@render bubble()}

		<div class={['flex gap-3', draft && 'ask-rise ask-rise-late']}>
			<span
				class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
				aria-hidden="true"
			>
				<Sparkles class="size-3.5" />
			</span>
			<div class="flex min-w-0 flex-1 flex-col gap-4">
				{#if lead && leadData}
					<ReadAs
						dimension={lead.dimension}
						reading={leadData.reading ?? []}
						query={lead.query}
						scope={scopeLabel}
					/>
				{/if}

				<WorkLine steps={trace} live={!!draft} {funnel} onCopy={answer ? copy : undefined} />

				{#if working}
					<div class="flex flex-col gap-2">
						<Skeleton class="h-9 w-2/5" />
						<Skeleton class="h-4 w-3/4" />
					</div>
				{/if}

				{#if lead || text}
					<AnswerLead
						block={lead}
						data={leadData}
						{text}
						citations={answer?.citations ?? []}
						{known}
						{onRef}
					/>
				{/if}

				{#each blocks as block (block.id)}
					<div class={['min-w-0', draft && 'ask-rise']}>
						<BlockCard
							{block}
							data={datas.get(block.id)}
							{threadId}
							{filtered}
							focused={focused === block.id}
							lead={block.id === lead?.id}
							{busy}
							{offline}
							onAbout={offline ? undefined : onAbout}
							onChange={onBlockChange}
							{onPin}
						/>
					</div>
				{/each}

				{#if unscanned && !draft}
					<p class="m-0 text-xs text-muted-foreground">{unscanned}</p>
				{/if}
			</div>
		</div>
	</article>
{/if}
