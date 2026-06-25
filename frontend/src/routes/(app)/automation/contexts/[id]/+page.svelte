<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Save from '@lucide/svelte/icons/save';
	import { Spinner } from '$lib/components/ui/spinner';

	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import { Input } from '$lib/components/ui/input';
	import * as Card from '$lib/components/ui/card';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CopyButton from '@/components/copy-button.svelte';
	import UnsavedChangesDialog from '@/components/unsaved-changes-dialog.svelte';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanContextsApi } from '$lib/api/scan-contexts';
	import { ROUTES } from '$lib/config/routes';

	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import ContextSections from '$lib/components/contexts/context-sections.svelte';
	import { buildContextSummary } from '$lib/components/contexts/context-summary';
	import { validateDraft, buildContextPayload } from '$lib/components/contexts/context-form';

	import {
		DEFAULT_SCAN_CONTEXT,
		type ScanContextRead,
		type ScanContextCreate,
		type ScanContextUpdate
	} from '$lib/types/scan-context';

	type Draft = ScanContextCreate;

	// route param
	let contextId = $derived(page.params.id);
	let isNew = $derived(contextId === 'new');

	// state
	let loaded = $state<ScanContextRead | null>(null);
	let draft = $state<Draft | null>(null);
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let isDuplicating = $state(false);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	let nameInputEl = $state<HTMLInputElement | null>(null);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let bypassGuard = false;

	let touchedSecrets = new SvelteSet<string>();

	let seedKey = $state(0);

	// dirty detection
	let baseline = $state<string>('');
	let hasUnsavedChanges = $derived.by(() => {
		if (!draft) return false;
		if (isNew) return true;
		return JSON.stringify(draft) !== baseline;
	});

	let validationIssue = $derived(draft ? validateDraft(draft) : null);
	let isValid = $derived(validationIssue === null);

	// load
	$effect(() => {
		const project = projectsStore.activeProject;
		const id = contextId;
		if (!project) return;
		untrack(() => {
			if (id === 'new') {
				initNew();
			} else if (id) {
				loadContext(id, project.id);
			}
		});
	});

	$effect(() => {
		if (isNew && draft && nameInputEl) nameInputEl.focus();
	});

	beforeNavigate((nav) => {
		if (bypassGuard) {
			bypassGuard = false;
			return;
		}
		if (!hasUnsavedChanges || showLeaveDialog) return;
		if (nav.willUnload) return;
		nav.cancel();
		pendingNav = () => {
			bypassGuard = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	$effect(() => {
		function onBeforeUnload(e: BeforeUnloadEvent) {
			if (hasUnsavedChanges) {
				e.preventDefault();
				e.returnValue = '';
			}
		}
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});

	function confirmLeave() {
		showLeaveDialog = false;
		const go = pendingNav;
		pendingNav = null;
		go?.();
	}

	function cancelLeave() {
		showLeaveDialog = false;
		pendingNav = null;
	}

	function onKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
			e.preventDefault();
			if (draft && !isSaving) handleSave();
		}
	}

	function initNew() {
		const d = DEFAULT_SCAN_CONTEXT();
		d.name = '';
		draft = d;
		loaded = null;
		baseline = '';
		touchedSecrets.clear();
		seedKey++;
	}

	function readToDraft(ctx: ScanContextRead): Draft {
		return {
			name: ctx.name,
			description: ctx.description,
			auth_type: ctx.auth_type,
			auth: { ...ctx.auth },
			extra_headers: ctx.extra_headers.map((h) => ({ ...h })),
			global_rate_limit_override: ctx.global_rate_limit_override,
			per_tool_rate_overrides: { ...ctx.per_tool_rate_overrides },
			thread_multiplier: ctx.thread_multiplier,
			timeout_multiplier: ctx.timeout_multiplier,
			excluded_subdomains: [...ctx.excluded_subdomains],
			excluded_paths: [...ctx.excluded_paths],
			excluded_ips: [...ctx.excluded_ips],
			included_subdomains: [...ctx.included_subdomains],
			follow_redirects_override: ctx.follow_redirects_override,
			http_protocol: ctx.http_protocol,
			proxy_id: ctx.proxy_id,
			compare_baseline_scan_id: ctx.compare_baseline_scan_id,
			scan_only_new_assets: ctx.scan_only_new_assets
		};
	}

	async function loadContext(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		touchedSecrets.clear();
		try {
			const cached = scanContextsStore.contexts.find((c) => c.id === id);
			if (cached) {
				loaded = cached;
				draft = JSON.parse(JSON.stringify(readToDraft(cached)));
				baseline = JSON.stringify(draft);
				seedKey++;
			}
			const fresh = await scanContextsApi.get(id, projectId);
			loaded = fresh;
			if (!hasUnsavedChanges) {
				draft = JSON.parse(JSON.stringify(readToDraft(fresh)));
				baseline = JSON.stringify(draft);
				seedKey++;
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load context';
		} finally {
			isLoading = false;
		}
	}

	function retryLoad() {
		const project = projectsStore.activeProject;
		if (project && contextId && !isNew) loadContext(contextId, project.id);
	}

	// section handlers
	function patchDraft(updates: Partial<Draft>) {
		if (!draft) return;
		draft = { ...draft, ...updates };
	}

	// save

	async function handleSave() {
		if (!draft || isSaving) return;
		if (validationIssue) {
			open[validationIssue.section] = true;
			toast.error(validationIssue.message);
			return;
		}
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}

		isSaving = true;
		try {
			if (isNew) {
				const created = await scanContextsStore.createContext(
					project.id,
					buildContextPayload(draft!, touchedSecrets)
				);
				if (created) {
					toast.success('Context created');
					loaded = created;
					draft = JSON.parse(JSON.stringify(readToDraft(created)));
					baseline = JSON.stringify(draft);
					touchedSecrets.clear();
					seedKey++;
					bypassGuard = true;
					goto(ROUTES.context(created.id), { replaceState: true });
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to create context');
				}
			} else {
				const update: ScanContextUpdate = buildContextPayload(draft!, touchedSecrets);
				delete update.compare_baseline_scan_id;
				delete update.scan_only_new_assets;
				const updated = await scanContextsStore.updateContext(contextId!, project.id, update);
				if (updated) {
					loaded = updated;
					draft = JSON.parse(JSON.stringify(readToDraft(updated)));
					baseline = JSON.stringify(draft);
					touchedSecrets.clear();
					seedKey++;
					toast.success('Context saved');
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to save context');
				}
			}
		} finally {
			isSaving = false;
		}
	}

	async function handleDuplicate() {
		const project = projectsStore.activeProject;
		if (!project || !contextId || isNew || isDuplicating) return;
		if (hasUnsavedChanges) {
			toast.warning('Unsaved changes are not copied — the saved version is duplicated.');
		}
		isDuplicating = true;
		try {
			const dup = await scanContextsStore.duplicateContext(contextId, project.id);
			if (dup?.id) {
				toast.success(`Duplicated as "${dup.name}"`);
				bypassGuard = true;
				goto(ROUTES.context(dup.id));
			} else {
				toast.error(scanContextsStore.error ?? 'Duplicate failed');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Duplicate failed');
		} finally {
			isDuplicating = false;
		}
	}

	function requestDelete() {
		if (!contextId || isNew) return;
		showDeleteDialog = true;
	}

	async function handleDelete() {
		if (!contextId || isNew) return;
		const project = projectsStore.activeProject;
		isDeleting = true;
		try {
			const ok = await scanContextsStore.deleteContext(contextId, project?.id);
			if (ok) {
				toast.success('Context deleted');
				showDeleteDialog = false;
				bypassGuard = true;
				goto(ROUTES.contexts);
			} else {
				toast.error(scanContextsStore.error ?? 'Delete failed');
			}
		} catch {
			toast.error('Delete failed');
		} finally {
			isDeleting = false;
		}
	}

	function handleBack() {
		goto(ROUTES.contexts);
	}

	// collapsible state
	let open = $state({
		identity: true,
		auth: true,
		rate: false,
		scope: false,
		runtime: false,
		proxy: false
	});

	let summary = $derived(draft ? buildContextSummary(draft) : '');
</script>

<svelte:window onkeydown={onKeydown} />

<div class="mx-auto w-full max-w-5xl space-y-6">
	{#if isLoading && !loaded && !isNew}
		<div class="flex items-center gap-2">
			<Skeleton class="h-8 w-8 rounded-md" />
			<Skeleton class="h-9 w-56" />
			<div class="ml-auto flex gap-2">
				<Skeleton class="h-8 w-24" />
				<Skeleton class="h-8 w-20" />
			</div>
		</div>
		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
			<div class="space-y-4">
				{#each Array(6) as _, i (i)}
					<Skeleton class="h-16 w-full rounded-xl" />
				{/each}
			</div>
			<Skeleton class="hidden h-48 w-full rounded-xl lg:block" />
		</div>
	{:else if loadError}
		<Empty.Root class="min-h-[50vh]">
			<Empty.Header>
				<Empty.Media class="size-[52px] rounded-xl bg-destructive/10">
					<AlertTriangle size={22} class="text-destructive" />
				</Empty.Media>
				<Empty.Title>Failed to load context</Empty.Title>
				<Empty.Description>{loadError}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<div class="flex items-center gap-2">
					<Button onclick={retryLoad} disabled={isLoading}>
						{#if isLoading}<Spinner class="h-3.5 w-3.5" />{/if}
						Retry
					</Button>
					<Button variant="outline" onclick={() => goto(ROUTES.contexts)}>Back to Contexts</Button>
				</div>
			</Empty.Content>
		</Empty.Root>
	{:else if draft}
		<div class="flex flex-wrap items-center gap-2">
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="h-8 w-8 shrink-0"
								aria-label="Back to Contexts"
								onclick={handleBack}
							>
								<ChevronLeft class="h-4 w-4" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content><p>Back to Contexts</p></Tooltip.Content>
				</Tooltip.Root>
				<Input
					bind:value={draft.name}
					bind:ref={nameInputEl}
					placeholder="Context name"
					onkeydown={(e) => e.key === 'Enter' && handleSave()}
					class="h-9 min-w-0 flex-1 sm:max-w-sm border-transparent bg-transparent text-base font-semibold shadow-none focus-visible:border-input focus-visible:bg-background"
				/>
			</div>
			<div class="flex flex-wrap items-center justify-end gap-2">
				{#if !isNew}
					{#if contextId}
						<CopyButton value={contextId} class="h-8 w-8" />
					{/if}
					<Button
						variant="ghost"
						size="sm"
						class="gap-1.5"
						disabled={isDuplicating}
						onclick={handleDuplicate}
					>
						{#if isDuplicating}
							<Spinner class="h-3.5 w-3.5" />
						{:else}
							<Copy class="h-3.5 w-3.5" />
						{/if}
						Duplicate
					</Button>
					<Button
						variant="ghost"
						size="sm"
						class="gap-1.5 text-destructive hover:text-destructive"
						onclick={requestDelete}
					>
						<Trash2 class="h-3.5 w-3.5" /> Delete
					</Button>
				{/if}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								class="gap-1.5"
								size="sm"
								disabled={isSaving || !isValid}
								onclick={handleSave}
							>
								{#if isSaving}
									<Spinner class="h-3.5 w-3.5" />
								{:else}
									<Save class="h-3.5 w-3.5" />
								{/if}
								Save
								{#if hasUnsavedChanges}<span class="dirty-dot"></span>{/if}
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>{validationIssue ? validationIssue.message : 'Save changes (⌘S)'}</p>
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
		</div>

		<p class="text-xs text-muted-foreground lg:hidden">{summary}</p>

		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
			<div class="space-y-4">
				<ContextSections
					draft={draft!}
					bind:open
					touched={touchedSecrets}
					onPatch={patchDraft}
					{seedKey}
				/>
			</div>

			<div class="hidden lg:block">
				<Card.Root class="lg:sticky lg:top-6">
					<Card.Header class="py-4">
						<Card.Title class="text-sm">Summary</Card.Title>
						<Card.Description class="text-xs">{summary}</Card.Description>
					</Card.Header>
					<Card.Content class="space-y-3 pb-5 text-xs text-muted-foreground">
						<div>
							<p class="mb-1 font-medium text-foreground">Merge notes</p>
							<ul class="space-y-1 pl-3">
								<li class="list-disc">Headers: engine ∪ context — context wins on conflict.</li>
								<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
							</ul>
						</div>
					</Card.Content>
				</Card.Root>
			</div>
		</div>
	{/if}
</div>

{#if !isNew}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete Context"
		description="Are you sure you want to delete '{draft?.name ??
			'this context'}'? This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={handleDelete}
	/>
{/if}

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	description="You have unsaved changes to this context. If you leave now, they will be lost."
	onOpenChange={(o) => {
		if (!o) cancelLeave();
	}}
	onConfirm={confirmLeave}
/>

<style>
	.dirty-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
		margin-left: 2px;
	}
</style>
