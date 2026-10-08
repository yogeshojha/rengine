<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import History from '@lucide/svelte/icons/history';
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import Plus from '@lucide/svelte/icons/plus';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import ScanLine from '@lucide/svelte/icons/scan-line';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import AskLanding from './ask-landing.svelte';
	import ThreadInfo from './thread-info.svelte';
	import AskTurn from './ask-turn.svelte';
	import EstateComposer, { type About } from './estate-composer.svelte';
	import FollowUps from './follow-ups.svelte';
	import HistorySheet from './history-sheet.svelte';
	import AskOff from './ask-off.svelte';
	import { scopeCount, scopeLabel, setLinkScan, setLinkValues } from './link-scope';
	import { applyFrame, draftText, newDraft, type Draft } from './thread-frames';
	import { estateApi } from '$lib/api/ask';
	import { ApiError, LONG_REQUEST_TIMEOUT_MS, NO_RESPONSE } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import { ABOUT_SEPARATOR, BLOCK_ID, BlockKind, MessageRole, StreamEvent } from '$lib/config/ask';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { surfaceSpec } from '$lib/config/surface';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { readStored, writeStored } from '$lib/utilities/storage';
	import { scopeFromParams } from '$lib/utilities/dashboard-scope';
	import { morph } from '$lib/utilities/view-transition';
	import type { TargetScope } from '$lib/utilities/surface-scope';
	import type {
		AnswerBlock,
		AskMessage,
		BlockData,
		EstateStarters,
		EstateStatus,
		EstateStarter,
		EstateStreamFrame,
		EstateThread,
		FollowUp,
		PinnedQuery
	} from '$lib/types/ask';

	const NO_ANSWER = 'The answer did not arrive. Check the api log.';
	const STAY = { replaceState: true, noScroll: true, keepFocus: true } as const;

	let project = $derived(projectsStore.activeProject);
	let projectId = $derived(project?.id ?? '');
	let projectSlug = $derived(project?.slug ?? '');
	let admin = $derived(auth.user?.is_superuser ?? false);

	let status = $state<EstateStatus | null>(null);
	let statusError = $state<string | null>(null);
	let starters = $state<EstateStarters | null>(null);
	let startersLoading = $state(false);
	let threads = $state<EstateThread[]>([]);
	let threadsLoading = $state(false);
	let scope = $state<TargetScope>({});
	let intelligent = $state(readStored(STORAGE_KEYS.askIntelligent) === '1');

	let thread = $state<EstateThread | null>(null);
	let messages = $state<AskMessage[]>([]);
	let fresh = $state(false);
	const datas = new SvelteMap<string, BlockData>();
	const opened = new SvelteSet<string>();
	let loadingThread = $state(false);
	let notFound = $state(false);
	let openError = $state('');
	let draft = $state<Draft | null>(null);
	let error = $state('');
	let loadError = $state('');
	let announce = $state('');
	let lastAsk = $state<{
		text: string;
		about: About | null;
		pinned: PinnedQuery | null;
	} | null>(null);
	let about = $state<About | null>(null);
	let focused = $state<string | null>(null);
	let historyOpen = $state(false);
	let creating = $state(false);
	let prefill = $state('');
	let composer = $state<EstateComposer | null>(null);
	let scanId = $state<string | null>(null);

	setLinkScan(() => thread?.scope.scan_id ?? null);
	setLinkValues(() => (thread?.scope.filtered ? thread.scope.links : null));
	let endEl = $state<HTMLDivElement | null>(null);

	let generation = 0;
	let openGeneration = 0;
	let threadsGeneration = 0;
	let opening: string | null = null;
	let carry = '';
	let startersGeneration = 0;
	let loadedProject = '';
	let controller: AbortController | null = null;
	let timer: ReturnType<typeof setTimeout> | null = null;

	let available = $derived(status?.available ?? false);
	let urlThread = $derived(page.url.searchParams.get('thread'));
	let urlQuestion = $derived(page.url.searchParams.get('q'));
	let turns = $derived.by(() => {
		const out: { q: AskMessage; a: AskMessage | null }[] = [];
		messages.forEach((m, i) => {
			if (m.role !== MessageRole.USER) return;
			const next = messages[i + 1];
			out.push({ q: m, a: next?.role === MessageRole.ASSISTANT ? next : null });
		});
		return out;
	});
	let heldBlocks = $derived(messages.flatMap((m) => m.blocks ?? []));
	let allBlocks = $derived([...heldBlocks, ...(draft?.blocks ?? [])]);
	let known = $derived(new Set(allBlocks.map((b) => b.id)));
	let followUps = $derived(
		messages.findLast((m) => m.role === MessageRole.ASSISTANT)?.follow_ups ?? []
	);
	let lastModel = $derived(
		messages.findLast((m) => m.role === MessageRole.ASSISTANT)?.model ?? status?.model ?? null
	);
	let filtered = $derived(thread?.scope.filtered ?? false);
	let showLanding = $derived(!thread && !loadingThread && !notFound && !draft);

	function loadStatus() {
		statusError = null;
		void estateApi
			.status()
			.then((s) => (status = s))
			.catch((e) => (statusError = e instanceof Error ? e.message : NO_RESPONSE));
	}

	$effect(() => {
		untrack(loadStatus);
	});

	$effect(() => {
		const id = projectId;
		if (!id || id === loadedProject) return;
		untrack(() => {
			if ((thread && thread.project_id !== id) || opening) void goto(ROUTES.ask());
			if (creating) cancel();
			loadedProject = id;
			threads = [];
			error = '';
			prefill = '';
			scope = {};
			scanId = null;
			void loadThreads(id);
		});
	});

	$effect(() => {
		const id = projectId;
		const s = $state.snapshot(scope) as TargetScope;
		const scan = scanId;
		if (!id) return;
		untrack(() => void loadStarters(id, s, scan));
	});

	$effect(() => {
		const id = urlThread;
		if (!projectId) return;
		untrack(() => {
			if (id && id !== (opening ?? thread?.id)) void open(id);
			else if (!id && (thread || notFound || draft || opening || loadingThread)) reset();
		});
	});

	$effect(() => {
		const q = urlQuestion;
		if (!q || !available || !projectId) return;
		untrack(() => {
			const asked = scopeFromParams(page.url.searchParams);
			void goto(ROUTES.ask(), STAY).then(() => {
				reset();
				scope = asked;
				scanId = null;
				void send(q);
			});
		});
	});

	$effect(() => () => cancel());

	async function loadThreads(id: string) {
		const mine = ++threadsGeneration;
		threadsLoading = true;
		try {
			const rows = await estateApi.threads(id);
			if (mine === threadsGeneration && id === projectId) threads = rows;
		} catch (e) {
			if (mine === threadsGeneration) toast.error((e as Error).message);
		} finally {
			if (mine === threadsGeneration) threadsLoading = false;
		}
	}

	async function loadStarters(id: string, s: TargetScope, scan: string | null) {
		const mine = ++startersGeneration;
		startersLoading = true;
		try {
			const found = await estateApi.starters(id, s, scan);
			if (mine === startersGeneration) starters = found;
		} catch {
			if (mine === startersGeneration) starters = null;
		} finally {
			if (mine === startersGeneration) startersLoading = false;
		}
	}

	function blockLabel(b: AnswerBlock): string {
		if (b.title) return b.title;
		if (b.kind === BlockKind.CVE) return b.cve ?? '';
		const spec = surfaceSpec(b.dimension ?? '');
		const noun = b.total === 1 ? spec?.noun : spec?.nounPlural;
		return `${b.total ?? ''} ${noun ?? ''}`.trim();
	}

	function aboutLabel(value: string | null | undefined): string | null {
		if (!value) return null;
		if (BLOCK_ID.test(value)) {
			const b = allBlocks.find((x) => x.id === value);
			return b ? `${value} · ${blockLabel(b)}` : value;
		}
		const at = value.indexOf(ABOUT_SEPARATOR);
		return at >= 0 ? value.slice(at + 1) : value;
	}

	function lastAbout(list: AnswerBlock[]): About | null {
		const b = list.at(-1);
		return b ? { id: b.id, label: blockLabel(b) } : null;
	}

	function reset() {
		cancel();
		fresh = false;
		openGeneration += 1;
		thread = null;
		messages = [];
		datas.clear();
		opened.clear();
		about = null;
		error = '';
		notFound = false;
		openError = '';
		focused = null;
		loadingThread = false;
		loadError = '';
		opening = null;
		lastAsk = null;
		prefill = carry;
		carry = '';
	}

	async function open(id: string) {
		cancel();
		const mine = ++openGeneration;
		fresh = false;
		opening = id;
		thread = null;
		loadingThread = true;
		notFound = false;
		openError = '';
		error = '';
		loadError = '';
		lastAsk = null;
		messages = [];
		datas.clear();
		opened.clear();
		focused = null;
		try {
			const detail = await estateApi.thread(id);
			if (mine !== openGeneration) return;
			if (detail.thread.project_id !== projectId) {
				notFound = true;
				return;
			}
			thread = detail.thread;
			messages = detail.messages;
			about = lastAbout(detail.messages.flatMap((m) => m.blocks ?? []));
		} catch (e) {
			if (mine !== openGeneration) return;
			thread = null;
			notFound = true;
			openError = e instanceof ApiError && e.status === 404 ? '' : (e as Error).message;
			return;
		} finally {
			if (mine === openGeneration) {
				loadingThread = false;
				opening = null;
			}
		}
		void tick().then(() => scrollToEnd(false));
		try {
			const fresh = await estateApi.blocks(id);
			if (mine !== openGeneration) return;
			for (const d of fresh) if (!datas.has(d.id)) datas.set(d.id, d);
		} catch (e) {
			if (mine === openGeneration) loadError = (e as Error).message;
		}
	}

	function viewport(): HTMLElement | null {
		return endEl?.closest<HTMLElement>('[data-slot="scroll-area-viewport"]') ?? null;
	}

	function smooth(): ScrollBehavior {
		return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
	}

	function scrollToEnd(animate = true) {
		const v = viewport();
		if (v) v.scrollTo({ top: v.scrollHeight, behavior: animate ? smooth() : 'auto' });
	}

	function goToBlock(id: string) {
		focused = id;
		const holder = turns.find((t) => t.a?.blocks?.some((b) => b.id === id));
		if (holder) opened.add(holder.q.id);
		void tick().then(() =>
			document.getElementById(`block-${id}`)?.scrollIntoView({ behavior: smooth(), block: 'start' })
		);
	}

	function unfold(id: string) {
		opened.add(id);
		void tick().then(() => document.getElementById(`turn-${id}`)?.focus());
	}

	function folded(index: number, id: string): boolean {
		if (opened.has(id)) return false;
		return index < turns.length - 1;
	}

	function cancel() {
		generation += 1;
		controller?.abort();
		controller = null;
		if (timer) clearTimeout(timer);
		timer = null;
		draft = null;
	}

	function scopeBody() {
		return {
			target_ids: scope.targetIds ?? [],
			organization_id: scope.organizationId ?? null,
			tag_id: scope.tagId ?? null,
			scan_id: scanId
		};
	}

	async function send(text: string, pinned: PinnedQuery | null = null) {
		if (draft || creating || !projectId || !available) return;
		error = '';
		notFound = false;
		prefill = '';
		const mine = ++generation;
		const asked = about;
		lastAsk = { text, about: asked, pinned };
		let settled = false;
		try {
			const begin = () => {
				draft = newDraft(text, asked?.id ?? null, intelligent);
				focused = null;
			};
			let id: string;
			if (!thread) {
				creating = true;
				const home = projectId;
				const created = await estateApi.create(home, scopeBody()).finally(() => (creating = false));
				if (mine !== generation || home !== projectId) {
					void estateApi.remove(created.id).catch(() => {});
					return;
				}
				id = created.id;
				await morph(() => {
					thread = created;
					begin();
				});
				void goto(ROUTES.ask({ thread: id }), STAY);
			} else {
				id = thread.id;
				begin();
			}
			void tick().then(() => {
				scrollToEnd();
				composer?.focus();
			});
			controller = new AbortController();
			const own = controller;
			timer = setTimeout(() => own.abort(), LONG_REQUEST_TIMEOUT_MS);
			await estateApi.ask(
				id,
				{ text, about: asked?.id ?? null, intelligent, pinned },
				(frame) => {
					if (mine !== generation) return;
					if (frame.event === StreamEvent.DONE || frame.event === StreamEvent.ERROR) settled = true;
					onFrame(frame);
				},
				own.signal
			);
			if (mine === generation && !settled) error = NO_ANSWER;
		} catch (e) {
			if (mine !== generation) return;
			error = failure(e as Error);
			if (!thread) prefill = text;
		} finally {
			if (mine === generation) {
				if (timer) clearTimeout(timer);
				timer = null;
				controller = null;
				draft = null;
			}
		}
	}

	function onFrame(frame: EstateStreamFrame) {
		if (frame.event === StreamEvent.DONE) {
			threadsGeneration += 1;
			threadsLoading = false;
			messages = [...messages, frame.data.question, frame.data.answer];
			fresh = true;
			announce = '';
			void tick().then(() => (announce = `Answer ready: ${frame.data.question.text}`));
			thread = frame.data.thread;
			threads = [frame.data.thread, ...threads.filter((t) => t.id !== frame.data.thread.id)];
			const added = frame.data.answer.blocks ?? [];
			if (added.length) about = lastAbout(added);
			draft = null;
			void tick().then(() => composer?.focus());
			return;
		}
		if (frame.event === StreamEvent.ERROR) {
			error = frame.data.message;
			return;
		}
		if (!draft) return;
		const next = applyFrame(draft, frame);
		draft = next.draft;
		if (next.data) datas.set(next.data.id, next.data);
	}

	function failure(e: Error): string {
		return e.name === 'AbortError' ? NO_ANSWER : e.message;
	}

	function stop() {
		const first = !messages.length;
		const text = lastAsk?.text ?? '';
		const id = thread?.id ?? null;
		cancel();
		if (!first) {
			if (text && !composer?.value().trim()) composer?.fill(text);
			else composer?.focus();
			return;
		}
		if (!id) {
			prefill = text;
			return;
		}
		void estateApi.remove(id).catch(() => {});
		carry = text;
		void goto(ROUTES.ask(), STAY);
	}

	function retry() {
		if (!lastAsk) return;
		about = lastAsk.about;
		void send(lastAsk.text, lastAsk.pinned);
	}

	function pin(text: string, pinned: PinnedQuery, from: string) {
		const b = allBlocks.find((x) => x.id === from);
		about = b ? { id: b.id, label: blockLabel(b) } : null;
		void send(text, pinned);
	}

	function followUp(item: FollowUp) {
		if (!item.dimension) {
			void send(item.text);
			return;
		}
		const b = allBlocks.find((x) => x.id === item.about);
		about = b ? { id: b.id, label: blockLabel(b) } : about;
		void send(item.text, {
			dimension: item.dimension,
			query: item.query ?? null,
			title: item.title ?? null
		});
	}

	function starter(s: EstateStarter) {
		about = null;
		void send(s.question, { dimension: s.dimension, query: s.query, title: s.statement });
	}

	function pointAt(value: string, label: string) {
		about = { id: value, label };
		void tick().then(() => composer?.focus());
	}

	function onBlockChange(block: AnswerBlock, data: BlockData, threadId: string) {
		if (threadId !== thread?.id) return;
		messages = messages.map((m) =>
			m.blocks?.some((b) => b.id === block.id)
				? { ...m, blocks: m.blocks.map((b) => (b.id === block.id ? block : b)) }
				: m
		);
		datas.set(block.id, data);
	}

	function setIntelligent(on: boolean) {
		intelligent = on;
		writeStored(STORAGE_KEYS.askIntelligent, on ? '1' : '0');
	}

	function openHistory() {
		historyOpen = true;
		if (projectId) void loadThreads(projectId);
	}

	function deleted(id: string) {
		threadsGeneration += 1;
		threadsLoading = false;
		threads = threads.filter((t) => t.id !== id);
		if (thread?.id === id) void goto(ROUTES.ask(), STAY);
	}

	function placeholder(on: About | null): string {
		if (!on) return 'Ask a follow-up';
		if (BLOCK_ID.test(on.id)) return `Ask about ${on.id}`;
		const noun = surfaceSpec(on.id.split(ABOUT_SEPARATOR, 1)[0])?.noun ?? 'row';
		return `Ask about this ${noun}`;
	}
</script>

{#snippet scopeChip()}
	{#if thread}
		<span
			class="inline-flex h-7 max-w-64 items-center gap-1.5 rounded-md border bg-muted/40 px-2 text-xs text-muted-foreground"
		>
			{#if thread.scope.scan_id}<ScanLine class="size-3 shrink-0" />{:else}<Crosshair
					class="size-3 shrink-0"
				/>{/if}
			<span class="truncate">{scopeLabel(thread.scope)}</span>
		</span>
	{/if}
{/snippet}

<div class="ask-stage relative -m-6 min-h-full p-6">
	<div
		class="ask-glow pointer-events-none absolute inset-x-0 top-0 h-[32rem]"
		aria-hidden="true"
	></div>
	<div class="relative">
		{#if showLanding}
			<AskLanding
				{status}
				{statusError}
				onRetryStatus={loadStatus}
				{starters}
				{startersLoading}
				recent={threads}
				{projectId}
				{projectSlug}
				{scope}
				{scanId}
				{intelligent}
				{admin}
				busy={!!draft || creating}
				{prefill}
				onScope={(s) => {
					scope = s;
					scanId = null;
				}}
				onScan={(id) => (scanId = id)}
				onIntelligent={setIntelligent}
				onAsk={(text) => void send(text)}
				onStarter={starter}
				onStop={stop}
				onOpen={(id) => void goto(ROUTES.ask({ thread: id }))}
				onHistory={openHistory}
			/>
			{#if error}
				<div class="mx-auto w-full max-w-3xl">
					<Alert.Root variant="destructive">
						<Alert.Title>No answer</Alert.Title>
						<Alert.Description>{error}</Alert.Description>
					</Alert.Root>
				</div>
			{/if}
		{:else if notFound && openError}
			<EmptyState icon={MessagesSquare} title="Thread not loaded" description={openError}>
				<Button size="sm" onclick={() => urlThread && void open(urlThread)}>Retry</Button>
				<Button href={ROUTES.ask()} variant="outline" size="sm"><Plus /> New question</Button>
			</EmptyState>
		{:else if notFound}
			<EmptyState icon={MessagesSquare} title="Thread not found">
				<Button href={ROUTES.ask()} size="sm"><Plus /> New question</Button>
			</EmptyState>
		{:else}
			<div class="mx-auto flex w-full max-w-4xl">
				<div class="flex min-w-0 flex-1 flex-col">
					<header class="flex items-center gap-3 pb-5">
						<div class="flex min-w-0 flex-1 items-center gap-2 text-xs text-muted-foreground">
							{#if thread}
								<span class="truncate">
									{[scopeLabel(thread.scope), scopeCount(thread.scope)].filter(Boolean).join(' · ')}
								</span>
							{:else}
								<Skeleton class="h-4 w-40" />
							{/if}
						</div>
						{#if thread}
							<ThreadInfo {thread} blocks={allBlocks} {datas} model={lastModel} onRef={goToBlock} />
						{/if}
						<Button variant="ghost" size="sm" class="h-8" onclick={openHistory}>
							<History /> History
						</Button>
						<Button variant="outline" size="sm" class="h-8" href={ROUTES.ask()}>
							<Plus /> New question
						</Button>
					</header>

					{#if loadingThread}
						<div class="flex flex-col gap-4">
							<Skeleton class="h-6 w-2/3" />
							<Skeleton class="h-4 w-full" />
							<Skeleton class="h-40 w-full rounded-lg" />
						</div>
					{:else}
						<div class="flex flex-col gap-10 pb-8">
							<p class="sr-only" aria-live="polite">{announce}</p>
							<div class="flex flex-col gap-10">
								{#each turns as t, i (t.q.id)}
									<AskTurn
										id={t.q.id}
										folded={folded(i, t.q.id)}
										onUnfold={() => unfold(t.q.id)}
										question={t.q.text}
										aboutLabel={aboutLabel(t.q.about)}
										intelligent={!!t.q.intelligent}
										answer={t.a}
										{datas}
										threadId={thread?.id ?? null}
										{filtered}
										scopeLabel={filtered && thread ? scopeLabel(thread.scope) : null}
										targets={thread?.scope.targets ?? 0}
										{focused}
										{known}
										busy={!!draft}
										offline={!available}
										onAbout={pointAt}
										onRef={goToBlock}
										{onBlockChange}
										onPin={pin}
									/>
								{/each}
							</div>

							{#if draft}
								<AskTurn
									question={draft.question}
									aboutLabel={aboutLabel(draft.about)}
									intelligent={draft.intelligent}
									draft={{ text: draftText(draft), trace: draft.trace, blocks: draft.blocks }}
									{datas}
									threadId={null}
									{filtered}
									scopeLabel={filtered && thread ? scopeLabel(thread.scope) : null}
									targets={thread?.scope.targets ?? 0}
									{focused}
									{known}
									busy
									offline={!available}
									onAbout={pointAt}
									onRef={goToBlock}
									{onBlockChange}
									onPin={pin}
								/>
								{#if draft.intelligent}
									<FollowUps items={[]} loading onAsk={() => {}} />
								{/if}
							{/if}

							{#if loadError}
								<Alert.Root variant="destructive">
									<Alert.Title>Blocks not loaded</Alert.Title>
									<Alert.Description>{loadError}</Alert.Description>
								</Alert.Root>
							{/if}

							{#if error}
								<div>
									<Alert.Root variant="destructive">
										<Alert.Title>No answer</Alert.Title>
										<Alert.Description>
											<span>{error}</span>
											{#if lastAsk && available}
												<Button variant="outline" size="sm" class="mt-2 w-fit" onclick={retry}
													>Retry</Button
												>
											{/if}
										</Alert.Description>
									</Alert.Root>
								</div>
							{/if}

							{#if !draft && !error && followUps.length}
								<FollowUps
									enter={fresh}
									items={followUps}
									disabled={!available}
									scopeValues={filtered ? (thread?.scope.links ?? []) : null}
									onAsk={followUp}
								/>
							{/if}
						</div>
					{/if}

					<div bind:this={endEl}></div>

					<div class="sticky bottom-0 z-10 -mx-2 bg-background px-2 pt-3 pb-1">
						{#if statusError && !status}
							<AskOff reason="AI status not loaded" detail={statusError} onRetry={loadStatus} />
						{:else if status && !available}
							<AskOff reason={status.off_reason ?? NO_RESPONSE} code={status.off_code} {admin} />
						{:else}
							<div class="ask-composer">
								<EstateComposer
									bind:this={composer}
									{about}
									{intelligent}
									busy={!!draft}
									disabled={!status || loadingThread}
									placeholder={placeholder(about)}
									leading={filtered ? scopeChip : undefined}
									onClearAbout={() => (about = null)}
									onIntelligent={setIntelligent}
									onSend={(text) => void send(text)}
									onStop={stop}
								/>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<HistorySheet
	open={historyOpen}
	{threads}
	loading={threadsLoading}
	active={thread?.id ?? null}
	onOpenChange={(o) => (historyOpen = o)}
	onPick={(id) => {
		historyOpen = false;
		void goto(ROUTES.ask({ thread: id }));
	}}
	onDeleted={deleted}
/>

<style>
	.ask-glow {
		background: radial-gradient(
			ellipse 60% 70% at 50% 0%,
			color-mix(in oklch, var(--primary) 15%, transparent),
			transparent 72%
		);
		opacity: 0.72;
	}

	.ask-stage:has(:global(.ask-composer textarea:focus)) .ask-glow {
		opacity: 1;
	}

	@media (prefers-reduced-motion: no-preference) {
		.ask-glow {
			transition: opacity 600ms ease-out;
		}
	}
</style>
