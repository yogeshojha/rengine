<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Save from '@lucide/svelte/icons/save';
	import Check from '@lucide/svelte/icons/check';
	import Play from '@lucide/svelte/icons/play';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import GitCompare from '@lucide/svelte/icons/git-compare';

	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ButtonGroup from '$lib/components/ui/button-group';
	import * as Kbd from '$lib/components/ui/kbd';
	import * as Resizable from '$lib/components/ui/resizable';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import LoadingButton from '@/components/loading-button.svelte';
	import UnsavedChangesDialog from '@/components/unsaved-changes-dialog.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import { scanContextsApi } from '$lib/api/scan-contexts';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { IsMobile } from '$lib/hooks/is-mobile.svelte';

	import ContextSections from '$lib/components/contexts/context-sections.svelte';
	import ContextEffect from '$lib/components/contexts/context-effect.svelte';
	import ContextFacets from '$lib/components/contexts/context-facets.svelte';
	import { validateDraft, buildContextPayload } from '$lib/components/contexts/context-form';
	import type { ContextFormSection } from '$lib/components/contexts/context-form';
	import { contextTemplate, templateDraft } from '$lib/components/contexts/context-templates';

	import type {
		ScanContextRead,
		ScanContextCreate,
		ScanContextUpdate
	} from '$lib/types/scan-context';

	type Draft = ScanContextCreate;

	const PAGE_SECTIONS: ContextFormSection[] = [
		'auth',
		'rate',
		'scope',
		'runtime',
		'proxy',
		'identity'
	];

	let contextId = $derived(page.params.id);
	let isNew = $derived(contextId === 'new');
	const isNarrow = new IsMobile(1100);
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

	let loaded = $state<ScanContextRead | null>(null);
	let draft = $state<Draft | null>(null);
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let isDuplicating = $state(false);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLaunch = $state(false);
	let mobileView = $state<'form' | 'effect'>('form');

	let nameInputEl = $state<HTMLInputElement | null>(null);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let bypassGuard = false;

	let touchedSecrets = new SvelteSet<string>();
	let seedKey = $state(0);

	let baseline = $state<string>('');
	let hasUnsavedChanges = $derived.by(() => {
		if (!draft) return false;
		if (isNew) return true;
		return JSON.stringify(draft) !== baseline;
	});

	let validationIssue = $derived(draft ? validateDraft(draft) : null);
	let isValid = $derived(validationIssue === null);
	let hasName = $derived(Boolean(draft?.name.trim()));
	let attemptedSave = $state(false);
	const showIssue = $derived(Boolean(validationIssue) && (attemptedSave || !isNew));

	let open = $state<Record<ContextFormSection, boolean>>({
		identity: false,
		auth: true,
		rate: false,
		scope: false,
		runtime: false,
		proxy: false
	});

	const proxyName = $derived(
		draft?.proxy_id
			? (proxiesStore.proxies.find((p) => p.id === draft?.proxy_id)?.name ?? null)
			: null
	);

	$effect(() => {
		if (!proxiesStore.hasFetched) proxiesStore.fetch();
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = contextId;
		if (!project) return;
		untrack(() => {
			if (id === 'new') initNew();
			else if (id) loadContext(id, project.id);
		});
	});

	$effect(() => {
		if (isNew && nameInputEl) nameInputEl.focus();
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

	onMount(() => {
		const onKey = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
				e.preventDefault();
				if (draft && !isSaving) handleSave();
			}
		};
		const onBeforeUnload = (e: BeforeUnloadEvent) => {
			if (!hasUnsavedChanges) return;
			e.preventDefault();
			e.returnValue = '';
		};
		window.addEventListener('keydown', onKey);
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => {
			window.removeEventListener('keydown', onKey);
			window.removeEventListener('beforeunload', onBeforeUnload);
		};
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

	function initNew() {
		const templateKey = page.url.searchParams.get('template');
		const template = contextTemplate(templateKey);
		draft = templateDraft(templateKey);
		loaded = null;
		baseline = '';
		touchedSecrets.clear();
		seedKey++;
		if (template) open = { ...open, auth: template.focus === 'auth', [template.focus]: true };
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

	function patchDraft(updates: Partial<Draft>) {
		if (!draft) return;
		draft = { ...draft, ...updates };
	}

	async function handleSave() {
		if (!draft || isSaving) return;
		if (validationIssue) {
			attemptedSave = true;
			if (validationIssue.section === 'identity') nameInputEl?.focus();
			else open[validationIssue.section] = true;
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
			toast.warning(
				'The duplicate is based on the last saved version. Unsaved changes are not included.'
			);
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
</script>

{#snippet form()}
	<section class="form">
		<ScrollArea class="min-h-0 flex-1">
			<div class="form-body">
				{#if draft}
					<ContextSections
						draft={draft!}
						bind:open
						touched={touchedSecrets}
						onPatch={patchDraft}
						sections={PAGE_SECTIONS}
						{seedKey}
					/>
				{/if}
			</div>
		</ScrollArea>
	</section>
{/snippet}

{#snippet effect()}
	<section class="side">
		<div class="side-head">
			<GitCompare size={13} class="text-muted-foreground" />
			<span class="side-title">Effect on an engine</span>
			<span class="side-sub">Engine settings this context overrides at scan time</span>
		</div>
		<div class="side-body">
			<ContextEffect {draft} />
		</div>
	</section>
{/snippet}

<div class="ctx-editor">
	{#if isLoading && !loaded && !isNew}
		<div class="state">
			<Skeleton class="h-6 w-56" />
			<Skeleton class="h-4 w-80" />
		</div>
	{:else if loadError}
		<Empty.Root class="flex-1">
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
					<Button variant="outline" onclick={() => goto(ROUTES.contexts)}>Back to contexts</Button>
				</div>
			</Empty.Content>
		</Empty.Root>
	{:else if draft}
		<header class="topbar">
			<div class="left">
				<Button
					variant="ghost"
					size="icon-sm"
					aria-label="Back to contexts"
					onclick={() => goto(ROUTES.contexts)}
				>
					<ArrowLeft size={15} />
				</Button>
				<Separator orientation="vertical" class="data-[orientation=vertical]:h-[18px]" />
				<Input
					bind:value={draft.name}
					bind:ref={nameInputEl}
					placeholder="Context name"
					aria-label="Context name"
					onkeydown={(e) => e.key === 'Enter' && handleSave()}
					class="h-8 min-w-0 flex-1 px-2 text-sm font-semibold sm:max-w-sm {isNew
						? ''
						: 'border-transparent bg-transparent shadow-none hover:border-input focus-visible:border-input focus-visible:bg-background dark:bg-transparent'}"
				/>
				{#if hasUnsavedChanges}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<span {...props} class="dot" aria-label="Unsaved changes"></span>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content class="text-xs">
							{isNew ? 'Not saved yet' : 'Unsaved changes'}
						</Tooltip.Content>
					</Tooltip.Root>
				{/if}
			</div>

			<div class="right">
				{#if !isNew}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="ghost" size="icon-sm" class="h-7 w-7" aria-label="More">
									<MoreHorizontal size={14} />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-40">
							<DropdownMenu.Item disabled={isDuplicating} onclick={handleDuplicate}>
								<Copy size={13} />
								Duplicate
							</DropdownMenu.Item>
							<DropdownMenu.Separator />
							<DropdownMenu.Item variant="destructive" onclick={() => (showDeleteDialog = true)}>
								<Trash2 size={13} />
								Delete
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}

				<ButtonGroup.Root>
					{#if !isNew}
						<Button
							variant="outline"
							size="sm"
							class="h-8 gap-1.5 text-xs"
							onclick={() => (showLaunch = true)}
						>
							<Play size={13} />
							Run
						</Button>
					{/if}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<span {...props} class="inline-flex">
									<LoadingButton
										size="sm"
										variant={hasUnsavedChanges ? 'default' : 'outline'}
										class="h-8 gap-1.5 text-xs {isNew ? '' : 'rounded-l-none border-l-0'}"
										loading={isSaving}
										loadingLabel="Saving…"
										disabled={!hasUnsavedChanges || !hasName || (!isValid && attemptedSave)}
										onclick={handleSave}
									>
										{#if hasUnsavedChanges}
											<Save size={13} />
											{isNew ? 'Create' : 'Save'}
											<Kbd.Group class="ml-0.5 hidden sm:inline-flex">
												<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">
													{isMac ? '⌘' : 'Ctrl'}
												</Kbd.Root>
												<Kbd.Root class="bg-primary-foreground/15 text-primary-foreground">
													S
												</Kbd.Root>
											</Kbd.Group>
										{:else}
											<Check size={13} />
											Saved
										{/if}
									</LoadingButton>
								</span>
							{/snippet}
						</Tooltip.Trigger>
						{#if validationIssue}
							<Tooltip.Content class="text-xs">{validationIssue.message}</Tooltip.Content>
						{/if}
					</Tooltip.Root>
				</ButtonGroup.Root>
			</div>
		</header>

		<div class="summary">
			<ContextFacets context={draft} {proxyName} variant="inline" class="min-w-0 flex-1" />
			{#if showIssue && validationIssue}
				<span class="issue"><AlertTriangle size={12} /> {validationIssue.message}</span>
			{/if}
		</div>

		{#if isNarrow.current}
			<div class="mobile-switch">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					value={mobileView}
					onValueChange={(v) => v && (mobileView = v as 'form' | 'effect')}
					aria-label="Editor view"
				>
					<ToggleGroup.Item value="form" class="h-7 gap-1.5 px-3 text-xs">
						<SlidersHorizontal size={13} />
						Settings
					</ToggleGroup.Item>
					<ToggleGroup.Item value="effect" class="h-7 gap-1.5 px-3 text-xs">
						<GitCompare size={13} />
						Effect
					</ToggleGroup.Item>
				</ToggleGroup.Root>
			</div>
			<div class="content">
				{#if mobileView === 'form'}
					{@render form()}
				{:else}
					{@render effect()}
				{/if}
			</div>
		{:else}
			<Resizable.PaneGroup
				direction="horizontal"
				autoSaveId={STORAGE_KEYS.contextSplit}
				class="content"
			>
				<Resizable.Pane defaultSize={60} minSize={40} order={1} class="pane">
					{@render form()}
				</Resizable.Pane>
				<Resizable.Handle class="handle" />
				<Resizable.Pane defaultSize={40} minSize={24} order={2} class="pane">
					{@render effect()}
				</Resizable.Pane>
			</Resizable.PaneGroup>
		{/if}

		{#if !isNew && contextId}
			<LaunchDialog bind:open={showLaunch} presetContextId={contextId} />
		{/if}
	{/if}
</div>

{#if !isNew}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete this context?"
		description={loaded?.usage?.schedules
			? `'${draft?.name ?? 'This context'}' is used by ${loaded.usage.schedules} scheduled scan${loaded.usage.schedules === 1 ? '' : 's'}. Those schedules will fail to launch without it. Completed scans and their results are unaffected. This action cannot be undone.`
			: `Removes '${draft?.name ?? 'this context'}' from the project. Completed scans and their results are unaffected. This action cannot be undone.`}
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={handleDelete}
	/>
{/if}

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	description="Your edits to this context have not been saved."
	onOpenChange={(o) => {
		if (!o) cancelLeave();
	}}
	onConfirm={confirmLeave}
/>

<style>
	:global([data-slot='scroll-area-viewport']:has(.ctx-editor) > div) {
		display: block;
		height: 100%;
	}
	:global([data-slot='scroll-area-viewport'] > div > main:has(.ctx-editor)) {
		height: 100%;
		padding: 0;
	}

	.ctx-editor {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		overflow: hidden;
	}

	.state {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 24px;
	}

	.topbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px 16px;
		flex-wrap: wrap;
		flex-shrink: 0;
		min-height: 52px;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border);
		background: var(--card);
	}
	.left,
	.right {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.left {
		flex: 1 1 auto;
	}
	.dot {
		display: inline-block;
		width: 7px;
		height: 7px;
		border-radius: 999px;
		background: var(--primary);
		flex-shrink: 0;
	}

	.summary {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px 14px;
		flex-shrink: 0;
		min-height: 36px;
		padding: 6px 16px;
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--muted) 45%, var(--background));
		font-size: 12px;
	}
	.issue {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: var(--destructive);
		white-space: nowrap;
	}

	.mobile-switch {
		display: flex;
		justify-content: center;
		flex-shrink: 0;
		padding: 6px 12px;
		border-bottom: 1px solid var(--border);
	}

	.ctx-editor :global(.content) {
		position: relative;
		display: flex;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}
	.ctx-editor :global(.pane) {
		display: flex;
		flex-direction: column;
		min-height: 0;
		min-width: 0;
	}
	.ctx-editor :global(.handle) {
		width: 1px;
		background: var(--border);
	}
	.ctx-editor :global(.handle[data-active]) {
		background: var(--primary);
	}

	.form {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
	}
	.form-body {
		max-width: 860px;
		padding: 16px 16px 56px;
	}

	.side {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		background: var(--card);
	}
	.side-head {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px 8px;
		flex-shrink: 0;
		min-height: 36px;
		padding: 6px 14px;
		border-bottom: 1px solid var(--border);
	}
	.side-title {
		font-size: 12px;
		font-weight: 600;
	}
	.side-sub {
		font-size: 11px;
		color: var(--muted-foreground);
	}
	.side-body {
		flex: 1;
		min-height: 0;
	}
</style>
