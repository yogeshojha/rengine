<script lang="ts">
	import { tick, untrack } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as Kbd from '$lib/components/ui/kbd';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import CodeEditor from '$lib/components/code-editor.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import {
		ACTION_KIND_LABELS,
		DEFAULT_ACTION_KIND,
		HANDOFF_KINDS,
		type ActionKind
	} from '$lib/config/connectors';
	import { MOD_KEY } from '$lib/utils';
	import { isEdited, lf, withBreaksOf } from './proxy-request';

	interface Props {
		open: boolean;
		title: string;
		kind: ActionKind;
		request: string;
		onSend: (kind: ActionKind, request: string | undefined) => Promise<boolean>;
	}

	let { open = $bindable(), title, kind, request, onSend }: Props = $props();

	let tool = $state<ActionKind>(DEFAULT_ACTION_KIND);
	let draft = $state('');
	let sending = $state(false);
	let discarding = $state(false);
	let editor = $state<CodeEditor | null>(null);

	const edited = $derived(isEdited(draft, request));

	$effect.pre(() => {
		if (!open) return;
		untrack(() => {
			tool = kind;
			draft = request;
			sending = false;
			discarding = false;
		});
	});

	function requestClose() {
		if (edited) discarding = true;
		else open = false;
	}

	function headEnd(): number | undefined {
		const at = lf(request).search(/\n\n/);
		return at < 0 ? undefined : at;
	}

	async function submit() {
		if (sending) return;
		sending = true;
		try {
			const ok = await onSend(tool, edited ? withBreaksOf(draft, request) : undefined);
			if (ok) open = false;
		} finally {
			sending = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key !== 'Enter' || !(e.metaKey || e.ctrlKey) || e.defaultPrevented) return;
		e.preventDefault();
		void submit();
	}
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : requestClose())}>
	<Dialog.Content
		class="gap-0 p-0 sm:max-w-2xl"
		onkeydown={onKey}
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			void tick().then(() => editor?.focus(headEnd()));
		}}
	>
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{title}</Dialog.Title>
		</Dialog.Header>

		<div class="flex flex-col gap-3 px-6 py-5">
			<div class="flex items-center justify-between gap-2">
				<Select.Root
					type="single"
					value={tool}
					onValueChange={(v) => {
						if (v) tool = v as ActionKind;
					}}
				>
					<Select.Trigger size="sm" class="h-7 gap-1.5 px-2.5 text-xs" aria-label="Tool">
						{ACTION_KIND_LABELS[tool]}
					</Select.Trigger>
					<Select.Content>
						{#each HANDOFF_KINDS as option (option)}
							<Select.Item value={option} label={ACTION_KIND_LABELS[option]} class="text-xs">
								{ACTION_KIND_LABELS[option]}
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2.5 text-xs"
					disabled={!edited}
					onclick={() => (draft = request)}
				>
					Reset
				</Button>
			</div>
			<CodeEditor
				bind:this={editor}
				bind:value={draft}
				lang="http"
				label="Request"
				onSubmit={submit}
			/>
		</div>

		<div class="flex justify-end gap-2 border-t bg-muted/30 px-6 py-3.5">
			<Button variant="outline" onclick={requestClose}>Cancel</Button>
			<LoadingButton loading={sending} loadingLabel="Sending" onclick={() => submit()}>
				Send
				<Kbd.Group class="ml-0.5 hidden sm:inline-flex">
					<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">{MOD_KEY}</Kbd.Root>
					<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">Enter</Kbd.Root>
				</Kbd.Group>
			</LoadingButton>
		</div>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={discarding}
	onOpenChange={(next) => (discarding = next)}
	onConfirm={() => {
		discarding = false;
		open = false;
	}}
/>
