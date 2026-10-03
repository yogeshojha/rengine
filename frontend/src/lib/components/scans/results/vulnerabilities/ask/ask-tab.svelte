<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import * as Alert from '$lib/components/ui/alert';
	import * as Bubble from '$lib/components/ui/bubble';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import NoteComposer from '$lib/components/notes/note-composer.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import AskComposer from './ask-composer.svelte';
	import AskMessageView from './ask-message.svelte';
	import AskStarters from './ask-starters.svelte';
	import AskTrace from './ask-trace.svelte';
	import EvidencePeek from './evidence-peek.svelte';
	import ThreadMenu from './thread-menu.svelte';
	import VerdictStrip from './verdict-strip.svelte';
	import { askApi, askBriefs, briefKey } from '$lib/api/ask';
	import { LONG_REQUEST_TIMEOUT_MS } from '$lib/api/client';
	import { Decision, EvidenceField, MessageRole, NextStep, StreamEvent } from '$lib/config/ask';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, type SurfaceDimension } from '$lib/config/surface';
	import { VULN_STATE_LABELS, VulnState } from '$lib/config/vulnerabilities';
	import type {
		AskBrief,
		AskFact,
		AskMessage,
		AskStreamFrame,
		AskSubject,
		AskThread,
		AskTraceStep
	} from '$lib/types/ask';

	interface Props {
		subject: AskSubject;
		loading?: boolean;
		queued?: string;
		onQueued?: () => void;
		onTriage?: (state: string) => void;
		onFileIssue?: () => void;
		onRescan?: () => void;
		onOpenEvidence?: () => void;
	}

	let {
		subject,
		loading = false,
		queued = '',
		onQueued,
		onTriage,
		onFileIssue,
		onRescan,
		onOpenEvidence
	}: Props = $props();

	const NO_ANSWER = 'The answer did not arrive. Check the api log.';

	let brief = $state<AskBrief | null>(null);
	let briefLoading = $state(false);
	let threadsLoading = $state(false);
	let threads = $state<AskThread[]>([]);
	let active = $state<AskThread | null>(null);
	let messages = $state<AskMessage[]>([]);
	let loadingThread = $state(false);
	let pending = $state<string | null>(null);
	let draft = $state<{ text: string; trace: AskTraceStep[] } | null>(null);
	let error = $state('');
	let lastQuestion = $state('');
	let factPeek = $state<AskFact | null>(null);
	let noteBody = $state<string | null>(null);
	let confirmDelete = $state(false);
	let confirmClear = $state(false);
	let deleting = $state(false);
	let clearing = $state(false);
	let endEl = $state<HTMLDivElement | null>(null);
	let composer = $state<AskComposer | null>(null);
	let noteComposer = $state<ReturnType<typeof NoteComposer> | null>(null);
	const noteGuard = new DiscardGuard(
		() => noteComposer?.dirty() ?? false,
		() => (noteBody = null)
	);
	let loadedFor = '';
	let briefFor = '';
	let briefOf = '';
	let generation = 0;
	let subjectGeneration = 0;
	let pickGeneration = 0;
	let briefGeneration = 0;
	let controller: AbortController | null = null;
	let timer: ReturnType<typeof setTimeout> | null = null;

	let key = $derived(`${subject.targetId}:${subject.dimension}:${subject.key}:${subject.scanId}`);
	let heldKey = $derived(briefKey(subject));
	let empty = $derived(!messages.length && !pending && !loadingThread && !threadsLoading);
	let draftText = $derived(draft ? draft.text.replace(/ ?\[(?:F|T|R)\d{1,3}\]/g, '') : '');
	let suggestion = $derived(
		messages.findLast((m) => m.role === MessageRole.ASSISTANT)?.suggestion ?? null
	);
	let noun = $derived(SURFACE[subject.dimension as SurfaceDimension].noun);
	let actions = $derived.by(() => {
		const out: { label: string; primary: boolean; run: () => void }[] = [];
		if (!suggestion || pending) return out;
		if (
			onTriage &&
			suggestion.decision === Decision.CONFIRMED &&
			subject.state !== VulnState.CONFIRMED
		) {
			out.push({
				label: `Mark ${VULN_STATE_LABELS[VulnState.CONFIRMED].toLowerCase()}`,
				primary: true,
				run: () => onTriage(VulnState.CONFIRMED)
			});
		}
		if (
			onTriage &&
			suggestion.decision === Decision.FALSE_POSITIVE &&
			subject.state !== VulnState.FALSE_POSITIVE
		) {
			out.push({
				label: `Mark ${VULN_STATE_LABELS[VulnState.FALSE_POSITIVE].toLowerCase()}`,
				primary: true,
				run: () => onTriage(VulnState.FALSE_POSITIVE)
			});
		}
		if (onFileIssue && suggestion.next === NextStep.FILE_ISSUE) {
			out.push({ label: 'File issue', primary: !out.length, run: onFileIssue });
		}
		if (onRescan && suggestion.next === NextStep.RESCAN) {
			out.push({ label: 'Rescan', primary: !out.length, run: onRescan });
		}
		return out;
	});

	$effect(() => {
		if (!subject.key || loadedFor === key) return;
		loadedFor = key;
		untrack(() => void load());
	});

	$effect(() => {
		if (!subject.key || briefFor === heldKey) return;
		briefFor = heldKey;
		untrack(() => void loadBrief());
	});

	$effect(() => {
		void messages.length;
		void draft?.text;
		void draft?.trace.length;
		void loadingThread;
		void tick().then(scrollToEnd);
	});

	$effect(() => {
		if (!queued || !brief?.available || pending || briefLoading || threadsLoading || loadingThread)
			return;
		const question = queued;
		onQueued?.();
		untrack(() => void send(question));
	});

	$effect(() => () => cancel());

	function scrollToEnd() {
		const viewport = endEl?.closest<HTMLElement>('[data-slot="scroll-area-viewport"]');
		if (viewport) viewport.scrollTo({ top: viewport.scrollHeight });
	}

	function cancel() {
		generation += 1;
		controller?.abort();
		controller = null;
		if (timer) clearTimeout(timer);
		timer = null;
		pending = null;
		draft = null;
	}

	async function load() {
		cancel();
		const mine = ++subjectGeneration;
		pickGeneration += 1;
		threadsLoading = true;
		loadingThread = false;
		error = '';
		threads = [];
		active = null;
		messages = [];
		try {
			const found = await askApi.threads(subject);
			if (mine !== subjectGeneration) return;
			threads = found;
			if (found.length) void pick(found[0]);
		} catch (e) {
			if (mine === subjectGeneration) error = (e as Error).message;
		} finally {
			if (mine === subjectGeneration) threadsLoading = false;
		}
	}

	async function loadBrief() {
		const mine = ++briefGeneration;
		if (briefOf !== key) {
			briefOf = key;
			brief = null;
		}
		factPeek = null;
		const held = askBriefs.peek(subject);
		if (held) {
			brief = held;
			briefLoading = false;
			return;
		}
		briefLoading = true;
		try {
			const found = await askBriefs.get(subject);
			if (mine === briefGeneration) brief = found;
		} catch (e) {
			if (mine === briefGeneration) error = (e as Error).message;
		} finally {
			if (mine === briefGeneration) briefLoading = false;
		}
	}

	async function pick(thread: AskThread) {
		const mine = ++pickGeneration;
		active = thread;
		messages = [];
		loadingThread = true;
		try {
			const detail = await askApi.thread(thread.id);
			if (mine !== pickGeneration) return;
			messages = detail.messages;
			active = detail.thread;
		} catch (e) {
			if (mine === pickGeneration) error = (e as Error).message;
		} finally {
			if (mine === pickGeneration) loadingThread = false;
		}
	}

	function startNew() {
		cancel();
		pickGeneration += 1;
		loadingThread = false;
		active = null;
		messages = [];
		error = '';
		void tick().then(() => composer?.focus());
	}

	async function removeThread() {
		if (!active || deleting) return;
		const id = active.id;
		deleting = true;
		try {
			await askApi.deleteThread(id);
			threads = threads.filter((t) => t.id !== id);
			startNew();
			confirmDelete = false;
		} catch (e) {
			toast.error((e as Error).message);
		} finally {
			deleting = false;
		}
	}

	async function clearHistory() {
		if (clearing) return;
		clearing = true;
		try {
			const { deleted } = await askApi.deleteThreads(subject);
			threads = [];
			startNew();
			confirmClear = false;
			toast.success(`${deleted} ${deleted === 1 ? 'thread' : 'threads'} removed`);
		} catch (e) {
			toast.error((e as Error).message);
		} finally {
			clearing = false;
		}
	}

	async function send(text: string) {
		if (pending) return;
		error = '';
		lastQuestion = text;
		const mine = ++generation;
		let settled = false;
		try {
			if (!active) {
				const created = await askApi.createThread(subject.projectId, {
					target_id: subject.targetId,
					dimension: subject.dimension,
					asset_key: subject.key
				});
				if (mine !== generation) return;
				threads = [created, ...threads];
				active = created;
			}
			const thread = active;
			pending = text;
			draft = { text: '', trace: [] };
			void tick().then(() => composer?.focus());
			controller = new AbortController();
			const own = controller;
			timer = setTimeout(() => own.abort(), LONG_REQUEST_TIMEOUT_MS);
			await askApi.ask(
				thread.id,
				{ text, scan_id: subject.scanId },
				(frame) => {
					if (mine !== generation) return;
					if (frame.event === StreamEvent.DONE || frame.event === StreamEvent.ERROR) settled = true;
					onFrame(frame);
				},
				own.signal
			);
			if (mine === generation && !settled) {
				error = NO_ANSWER;
				if (active) void pick(active);
			}
		} catch (e) {
			if (mine !== generation) return;
			error = (e as Error).message;
			if (active) void pick(active);
		} finally {
			if (mine === generation) {
				if (timer) clearTimeout(timer);
				timer = null;
				controller = null;
				pending = null;
				draft = null;
			}
		}
	}

	function onFrame(frame: AskStreamFrame) {
		if (!draft) return;
		switch (frame.event) {
			case StreamEvent.TRACE: {
				const { index, ...step } = frame.data;
				const trace = [...draft.trace];
				trace[index] = step;
				draft = { ...draft, trace };
				break;
			}
			case StreamEvent.DELTA:
				draft = { ...draft, text: draft.text + frame.data.text };
				break;
			case StreamEvent.DONE:
				messages = [...messages, frame.data.question, frame.data.answer];
				active = frame.data.thread;
				threads = threads.map((t) => (t.id === frame.data.thread.id ? frame.data.thread : t));
				break;
			case StreamEvent.ERROR:
				error = frame.data.message;
				break;
		}
	}
</script>

<div class="sticky top-0 z-10 flex flex-col bg-card">
	<div class="flex items-center justify-between gap-3 border-b px-5 py-1.5">
		<ThreadMenu
			{threads}
			{active}
			{noun}
			onPick={(t) => {
				cancel();
				void pick(t);
			}}
			onNew={startNew}
			onClear={() => (confirmClear = true)}
		/>
		{#if active}
			<div class="flex shrink-0 items-center gap-1">
				<Button
					variant="ghost"
					size="sm"
					class="h-7 gap-1.5 px-2 text-xs"
					onclick={startNew}
					aria-label="New thread"
				>
					<Plus />
					New
				</Button>
				<Hint text="Delete thread">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7 text-muted-foreground"
							onclick={() => (confirmDelete = true)}
							aria-label="Delete thread"
						>
							<Trash2 />
						</Button>
					{/snippet}
				</Hint>
			</div>
		{/if}
	</div>

	<VerdictStrip
		{brief}
		loading={(briefLoading && !brief) || loading}
		onFact={(f) => (factPeek = factPeek?.n === f.n ? null : f)}
	/>

	{#if factPeek?.field}
		<div class="border-b px-5 py-3">
			<EvidencePeek
				field={factPeek.field}
				lines={factPeek.lines}
				text={factPeek.field === EvidenceField.REQUEST
					? (subject.request ?? null)
					: (subject.response ?? null)}
				mark={factPeek.n}
				onOpen={onOpenEvidence}
				capped
			/>
		</div>
	{/if}
</div>

<div class="flex flex-col gap-5 p-5">
	{#if brief && !brief.available}
		<Alert.Root>
			<Alert.Title>{brief.off_reason}</Alert.Title>
			<Alert.Description>
				<a href={ROUTES.ai('connection')} class="font-medium text-primary">Open AI settings</a>
			</Alert.Description>
		</Alert.Root>
	{/if}

	{#if loadingThread || threadsLoading}
		<div class="flex flex-col gap-3">
			<Skeleton class="h-9 w-3/5 self-end" />
			<Skeleton class="h-4 w-full" />
			<Skeleton class="h-4 w-11/12" />
			<Skeleton class="h-4 w-2/3" />
		</div>
	{:else}
		{#if empty}
			<AskStarters {subject} onAsk={(question) => void send(question)} />
		{/if}
		<div class="contents" role="log" aria-live="polite">
			{#each messages as message (message.id)}
				<AskMessageView
					{message}
					request={subject.request ?? null}
					response={subject.response ?? null}
					{onOpenEvidence}
					onSave={(text) => (noteBody = text)}
				/>
			{/each}
		</div>
	{/if}

	{#if pending}
		<Bubble.Root align="end" variant="muted" class="max-w-[85%] self-end">
			<Bubble.Content class="whitespace-pre-wrap">{pending}</Bubble.Content>
		</Bubble.Root>
	{/if}

	{#if draft}
		<div class="flex flex-col gap-3">
			{#if draft.trace.length}
				<AskTrace steps={draft.trace} live />
			{/if}
			{#if draftText}
				<p class="m-0 text-sm leading-relaxed whitespace-pre-wrap wrap-anywhere">{draftText}</p>
			{:else}
				<div class="flex flex-col gap-2">
					<Skeleton class="h-4 w-full" />
					<Skeleton class="h-4 w-4/5" />
				</div>
			{/if}
		</div>
	{/if}

	{#if error}
		<Alert.Root variant="destructive">
			<Alert.Title>No answer</Alert.Title>
			<Alert.Description>
				<span>{error}</span>
				{#if lastQuestion && brief?.available}
					<Button
						variant="outline"
						size="sm"
						class="mt-2 w-fit"
						onclick={() => void send(lastQuestion)}>Retry</Button
					>
				{/if}
			</Alert.Description>
		</Alert.Root>
	{/if}

	<div bind:this={endEl}></div>
</div>

<div class="sticky bottom-0 flex flex-col border-t bg-card">
	{#if actions.length}
		<div class="flex flex-wrap items-center gap-2 border-b bg-muted/30 px-5 py-2">
			<span class="mr-1 text-2xs tracking-wide text-muted-foreground uppercase">Suggested</span>
			{#each actions as action (action.label)}
				<Button
					size="sm"
					variant={action.primary ? 'default' : 'outline'}
					class="h-7 text-xs"
					onclick={action.run}>{action.label}</Button
				>
			{/each}
		</div>
	{/if}
	<div class="px-5 pt-3 pb-4">
		<AskComposer
			bind:this={composer}
			placeholder="Ask about this {noun}"
			disabled={!brief?.available}
			busy={!!pending}
			onSend={(text) => void send(text)}
			onStop={cancel}
		/>
	</div>
</div>

<ConfirmDialog
	bind:open={confirmDelete}
	title="Delete thread"
	description="The thread and its messages are removed."
	confirmLabel="Delete"
	loadingLabel="Deleting"
	loading={deleting}
	destructive
	onOpenChange={(o) => (confirmDelete = o)}
	onConfirm={() => void removeThread()}
/>

<ConfirmDialog
	bind:open={confirmClear}
	title="Clear history"
	description="Every thread on this {noun} and its messages are removed."
	confirmLabel="Clear"
	loadingLabel="Clearing"
	loading={clearing}
	destructive
	onOpenChange={(o) => (confirmClear = o)}
	onConfirm={() => void clearHistory()}
/>

<Dialog.Root
	bind:open={
		() => noteBody !== null,
		(next) => {
			if (!next) noteGuard.close();
		}
	}
>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Save to notes</Dialog.Title>
		</Dialog.Header>
		{#if noteBody !== null}
			<NoteComposer
				bind:this={noteComposer}
				anchor={{
					targetId: subject.targetId,
					scanId: subject.scanId,
					dimension: subject.dimension,
					assetKey: subject.key,
					assetLabel: subject.label
				}}
				initialBody={noteBody}
				autofocus
				onSaved={() => {
					noteBody = null;
					toast.success('Note saved');
				}}
				onCancel={() => (noteBody = null)}
			/>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={noteGuard.asking}
	onOpenChange={(next) => (noteGuard.asking = next)}
	onConfirm={noteGuard.discard}
/>
