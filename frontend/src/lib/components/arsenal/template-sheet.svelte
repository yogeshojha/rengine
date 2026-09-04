<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Copy from '@lucide/svelte/icons/copy';
	import Lock from '@lucide/svelte/icons/lock';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Textarea } from '$lib/components/ui/textarea';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { PROTOCOL_LABELS, TEMPLATE_ORIGIN_LABELS } from '$lib/config/vulnerabilities';
	import type { TemplateSource, VulnTemplateRead } from '$lib/types/vuln-template';

	interface Props {
		template: VulnTemplateRead | null;
		creating?: boolean;
		onOpenChange: (open: boolean) => void;
		onSaved: () => void;
	}

	let { template, creating = false, onOpenChange, onSaved }: Props = $props();

	const STARTER = `id: custom-check

info:
  name: Custom check
  severity: medium
  description: What this check detects.
  tags: custom

http:
  - method: GET
    path:
      - "{{BaseURL}}/"
    matchers:
      - type: word
        part: body
        words:
          - "example"
`;

	let source = $state<TemplateSource | null>(null);
	let draft = $state('');
	let original = $state('');
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let confirming = $state(false);
	let contentEl = $state<HTMLElement | null>(null);
	let editorEl = $state<HTMLTextAreaElement | null>(null);

	let open = $derived(creating || !!template);
	let editable = $derived(creating || source?.editable === true);
	let dirty = $derived(editable && draft !== original);

	$effect(() => {
		const row = template;
		const isNew = creating;
		untrack(() => {
			error = null;
			source = null;
			if (isNew) {
				draft = STARTER;
				original = STARTER;
				return;
			}
			if (!row) return;
			draft = '';
			original = '';
			void load(row.id);
		});
	});

	$effect(() => {
		const el = editorEl;
		if (el && !loading) untrack(() => el.focus({ preventScroll: true }));
	});

	async function load(id: string) {
		loading = true;
		try {
			const res = await vulnTemplatesApi.source(id);
			source = res;
			draft = res.content;
			original = res.content;
		} catch {
			error = 'Could not read this check from the library.';
		} finally {
			loading = false;
		}
	}

	async function save() {
		saving = true;
		error = null;
		try {
			if (creating) {
				const res = await vulnTemplatesApi.upload([
					{ filename: `${filenameOf(draft)}.yaml`, content: draft }
				]);
				const rejected = res.rejected[0];
				if (rejected) {
					error = rejected.reason;
					return;
				}
				toast.success(`${res.accepted[0]?.name ?? 'The check'} was added to the library`);
			} else if (template) {
				const updated = await vulnTemplatesApi.saveSource(template.id, draft);
				toast.success(`Saved ${updated.name}`);
			}
			original = draft;
			onSaved();
			onOpenChange(false);
		} catch (err) {
			error = err instanceof Error ? err.message : 'The check could not be saved.';
		} finally {
			saving = false;
		}
	}

	function filenameOf(text: string): string {
		const match = /^id:\s*(\S+)/m.exec(text);
		return (
			(match?.[1] ?? 'custom-check').replace(/[^a-zA-Z0-9-_.]/g, '').slice(0, 60) || 'custom-check'
		);
	}

	function requestClose(next: boolean) {
		if (next) return;
		if (dirty) {
			confirming = true;
			return;
		}
		onOpenChange(false);
	}

	async function copy() {
		if (await writeClipboard(draft)) toast.success('Copied');
	}
</script>

<Sheet.Root {open} onOpenChange={requestClose}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-3xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		<Sheet.Header class="gap-2 border-b px-5 pt-5 pr-12 pb-4">
			<div class="flex items-start gap-2">
				{#if template}
					<span class="flex h-6 shrink-0 items-center">
						<SeverityMark severity={template.severity} showLabel={false} size="md" />
					</span>
				{/if}
				<div class="min-w-0 flex-1">
					<Sheet.Title class="text-base leading-6 font-medium wrap-anywhere">
						{creating ? 'New check' : (template?.name ?? '')}
					</Sheet.Title>
					<Sheet.Description class="mt-0.5 font-mono text-xs wrap-anywhere">
						{creating
							? 'Saved as a custom template'
							: (source?.path ?? template?.template_id ?? '')}
					</Sheet.Description>
				</div>
			</div>
			{#if template}
				<div class="flex flex-wrap items-center gap-2">
					<Badge variant={template.origin === 'custom' ? 'info' : 'outline'} class="font-normal">
						{TEMPLATE_ORIGIN_LABELS[template.origin] ?? template.origin}
					</Badge>
					<Badge variant="outline" class="font-normal">
						{PROTOCOL_LABELS[template.protocol] ?? template.protocol}
					</Badge>
					{#each template.tags.slice(0, 5) as tag (tag)}
						<Badge variant="outline" class="font-normal">{tag}</Badge>
					{/each}
				</div>
			{/if}
		</Sheet.Header>

		<div class="flex min-h-0 flex-1 flex-col gap-3 px-5 py-4">
			{#if !editable && !loading}
				<div class="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2">
					<Lock class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
					<p class="text-xs text-muted-foreground">
						Project templates are read-only. A library sync replaces them, so changes made here are
						lost. Copy the source into a custom template to modify it.
					</p>
				</div>
			{/if}

			{#if error}
				<div
					class="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2"
				>
					<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-destructive" />
					<p class="text-xs wrap-anywhere">{error}</p>
				</div>
			{/if}

			{#if loading}
				<Skeleton class="min-h-0 flex-1" />
			{:else if editable}
				<Textarea
					bind:ref={editorEl}
					bind:value={draft}
					spellcheck={false}
					aria-label="Check source"
					class="min-h-0 flex-1 resize-none font-mono text-xs leading-5"
				/>
			{:else}
				<ScrollArea class="min-h-0 flex-1 rounded-md border">
					<pre
						class="p-3 font-mono text-xs leading-5 whitespace-pre-wrap wrap-anywhere">{draft}</pre>
				</ScrollArea>
			{/if}
		</div>

		<Sheet.Footer class="flex-row items-center justify-between gap-2 border-t px-5 py-3">
			<Hint text="Copy the source">
				{#snippet child(props)}
					<Button {...props} variant="ghost" size="sm" class="gap-2" onclick={copy}>
						<Copy class="size-4" /> Copy
					</Button>
				{/snippet}
			</Hint>
			<div class="flex items-center gap-2">
				<Button variant="outline" size="sm" onclick={() => requestClose(false)}>
					{editable ? 'Cancel' : 'Close'}
				</Button>
				{#if editable}
					<LoadingButton
						size="sm"
						loading={saving}
						loadingLabel="Saving…"
						disabled={!dirty && !creating}
						onclick={save}
					>
						{creating ? 'Add check' : 'Save changes'}
					</LoadingButton>
				{/if}
			</div>
		</Sheet.Footer>
	</Sheet.Content>
</Sheet.Root>

<UnsavedChangesDialog
	open={confirming}
	onOpenChange={(value) => (confirming = value)}
	onConfirm={() => {
		confirming = false;
		onOpenChange(false);
	}}
/>
