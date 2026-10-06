<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Play from '@lucide/svelte/icons/play';
	import Radar from '@lucide/svelte/icons/radar';
	import SearchIcon from '@lucide/svelte/icons/search';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import { setMode, resetMode } from 'mode-watcher';
	import { toast } from 'svelte-sonner';

	import { ROUTES, UUID_REGEX, projectSwitchRedirect } from '$lib/config/routes';
	import { SURFACE } from '$lib/config/surface';
	import { TOOLBOX_ICON } from '$lib/config/toolbox';
	import {
		buildCommands,
		GROUP_LABELS,
		matchCommand,
		PALETTE_GROUPS
	} from '$lib/config/command-palette';
	import {
		assetLookups,
		COMMAND_PREFIX,
		cveId,
		cveLookups,
		hashLookups,
		isCve,
		isHexHash,
		isQuestion,
		queryDimensions,
		searchHref,
		type AssetLookup,
		type PaletteScope
	} from '$lib/utilities/palette';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { plural } from '$lib/utilities/strings';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { estateApi } from '$lib/api/ask';
	import { targetsApi } from '$lib/api/targets';
	import { scansApi } from '$lib/api/scans';
	import { auth } from '$lib/stores/auth.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { QUERY_SCHEMAS, loadAllSchemas } from '$lib/stores/query-schema.svelte';
	import { recent } from '$lib/stores/recent.svelte';
	import type { Project } from '$lib/types/project';
	import type { ScanRead } from '$lib/types/scan';
	import { TargetType, type Target as TargetEntity } from '$lib/types/target';
	import { IS_MAC } from '$lib/utils';

	let {
		onAddTarget,
		onScan,
		onToolbox
	}: {
		onAddTarget: () => void;
		onScan: (value?: string) => void;
		onToolbox: (value: string) => void;
	} = $props();

	const MAX_COMMANDS = 6;
	const MAX_QUERY_DIMENSIONS = 3;
	const MAX_RECENTS = 5;

	let commandOpen = $state(false);
	let askReady = $state(false);
	let raw = $state('');
	let searchResults = $state<TargetEntity[]>([]);
	let searching = $state(false);
	let validType = $state<TargetType | null>(null);
	let validValue = $state<string | null>(null);
	let cancelTarget = $state<ScanRead | null>(null);
	let cancelAllOpen = $state(false);
	let cancelling = $state(false);

	const searchShortcut = IS_MAC ? '⌘K' : 'Ctrl+K';

	const activeProject = $derived(projectsStore.activeProject);
	const projectId = $derived(activeProject?.id ?? '');

	const commandMode = $derived(raw.trimStart().startsWith(COMMAND_PREFIX));
	const term = $derived((commandMode ? raw.trimStart().slice(COMMAND_PREFIX.length) : raw).trim());

	const scope = $derived.by<PaletteScope>(() => {
		const path = page.url.pathname;
		const id = page.params.id;
		if (id && UUID_REGEX.test(id)) {
			const label =
				breadcrumbStore.getLabel(id) ??
				(breadcrumbStore.getTrail(id) ?? []).map((crumb) => crumb.label).join(' · ');
			if (path === ROUTES.scan(id)) {
				return {
					kind: 'scan',
					label: label || 'This run',
					scanId: id,
					targetId: null,
					targetValue: null
				};
			}
			if (path === ROUTES.target(id)) {
				return {
					kind: 'target',
					label: label || 'This target',
					scanId: null,
					targetId: id,
					targetValue: label || null
				};
			}
		}
		return {
			kind: 'project',
			label: activeProject?.name ?? '',
			scanId: null,
			targetId: null,
			targetValue: null
		};
	});

	$effect(() => {
		const { kind, label, scanId, targetId } = scope;
		const pid = projectId;
		if (!pid || !label || kind === 'project') return;
		const id = scanId ?? targetId;
		if (!id) return;
		untrack(() =>
			recent.record({ kind: kind === 'scan' ? 'scan' : 'target', id, label, projectId: pid })
		);
	});

	$effect(() => {
		if (!commandOpen) return;
		untrack(() => {
			void loadAllSchemas();
			void estateApi
				.status()
				.then((s) => (askReady = s.available))
				.catch(() => (askReady = false));
		});
	});

	$effect(() => {
		const value = commandMode ? '' : term;
		if (value.length < 2) {
			searchResults = [];
			validType = null;
			validValue = null;
			searching = false;
			return;
		}
		searching = true;
		const slug = projectsStore.activeProject?.slug;
		let stale = false;
		const t = setTimeout(async () => {
			try {
				const [results, check] = await Promise.all([
					targetsApi.searchByValue(value, slug),
					/\s/.test(value)
						? Promise.resolve(null)
						: targetsApi.validate({ target_value: value }).catch(() => null)
				]);
				if (stale) return;
				searchResults = results;
				validType = check?.valid ? check.target_type : null;
				validValue = check?.valid ? check.target_value || value : null;
			} catch {
				if (stale) return;
				searchResults = [];
				validType = null;
				validValue = null;
			} finally {
				if (!stale) searching = false;
			}
		}, SEARCH_DEBOUNCE_MS);
		return () => {
			stale = true;
			clearTimeout(t);
		};
	});

	$effect(() => {
		if (!commandOpen) {
			raw = '';
			searchResults = [];
			validType = null;
			validValue = null;
		}
	});

	$effect(() => {
		const handleKeydown = (e: KeyboardEvent) => {
			if (e.shiftKey) return;
			if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
				e.preventDefault();
				commandOpen = !commandOpen;
			}
		};
		document.addEventListener('keydown', handleKeydown);
		return () => document.removeEventListener('keydown', handleKeydown);
	});

	function close() {
		commandOpen = false;
	}

	function run(action: () => void) {
		close();
		action();
	}

	function switchProject(project: Project) {
		const redirect = projectSwitchRedirect(page.url.pathname, project.slug);
		if (redirect) void goto(redirect);
		else projectsStore.setActiveProject(project);
	}

	async function copyLink() {
		const ok = await writeClipboard(window.location.href);
		if (ok) toast.success('Link copied');
		else toast.error('Link not copied');
	}

	async function pause(scan: ScanRead) {
		if (await liveScans.pause(scan)) toast.success('Scan paused');
		else toast.error('Scan not paused');
	}

	async function resume(scan: ScanRead) {
		if (await liveScans.resume(scan)) toast.success('Scan resumed');
		else toast.error('Scan not resumed');
	}

	async function confirmCancel() {
		const scan = cancelTarget;
		if (!scan) return;
		cancelling = true;
		const ok = await liveScans.cancel(scan);
		cancelling = false;
		if (ok) {
			cancelTarget = null;
			toast.success('Scan cancelled');
		} else toast.error('Scan not cancelled');
	}

	async function confirmCancelAll() {
		if (!projectId) return;
		cancelling = true;
		try {
			const { cancelled } = await scansApi.cancelAll(projectId);
			liveScans.refresh();
			cancelAllOpen = false;
			toast.success(`${plural(cancelled, 'scan')} cancelled`);
		} catch {
			toast.error('Scans not cancelled');
		} finally {
			cancelling = false;
		}
	}

	const commands = $derived(
		buildCommands({
			scope,
			liveScans: liveScans.scans,
			projects: projectsStore.projects,
			activeProjectId: projectId,
			has: (capability) => capabilitiesStore.has(capability),
			isAdmin: auth.user?.is_superuser ?? false,
			actions: {
				go: (href) => void goto(href),
				addTarget: onAddTarget,
				startScan: (value) => onScan(value),
				pause: (scan) => void pause(scan),
				resume: (scan) => void resume(scan),
				cancel: (scan) => (cancelTarget = scan),
				cancelAll: () => (cancelAllOpen = true),
				copyLink: () => void copyLink(),
				switchProject: (project) => switchProject(project),
				setTheme: (mode) => (mode === 'system' ? resetMode() : setMode(mode))
			}
		})
	);

	const matched = $derived(commands.filter((c) => matchCommand(c, term)));

	const grouped = $derived(
		PALETTE_GROUPS.map((group) => ({
			group,
			items: matched.filter((c) => c.group === group)
		})).filter((entry) => entry.items.length > 0)
	);

	const queryMatches = $derived.by(() => {
		if (commandMode || !term) return [];
		return queryDimensions(term, (dimension) => {
			const store = QUERY_SCHEMAS[dimension];
			return (name: string) => store.byName.has(name);
		}).slice(0, MAX_QUERY_DIMENSIONS);
	});

	const lookups = $derived.by<AssetLookup[]>(() => {
		if (commandMode || !term) return [];
		if (isCve(term)) return cveLookups(term);
		if (isHexHash(term)) return hashLookups(term);
		return assetLookups(validValue ?? term, validType);
	});

	const visits = $derived(projectId ? recent.opened(projectId).slice(0, MAX_RECENTS) : []);
	const searches = $derived(commandOpen ? recent.searches() : []);

	const showRecents = $derived(!commandMode && !term);
	const starters = $derived(
		showRecents ? matched.filter((c) => c.group === 'run' || c.group === 'create') : []
	);
</script>

<Button
	variant="ghost"
	size="icon"
	class="@xl/topbar:hidden"
	aria-label="Search"
	onclick={() => (commandOpen = true)}
>
	<SearchIcon class="h-4 w-4" />
</Button>
<Button
	variant="outline"
	class="relative hidden h-9 justify-start rounded-md text-sm text-muted-foreground @xl/topbar:inline-flex @xl/topbar:w-64 @4xl/topbar:w-80"
	onclick={() => (commandOpen = true)}
>
	<SearchIcon class="h-4 w-4" />
	<span>Search…</span>
	<kbd
		class="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-2xs font-medium opacity-100 sm:flex"
	>
		{searchShortcut}
	</kbd>
</Button>

<Dialog.Root bind:open={commandOpen}>
	<Dialog.Content class="overflow-hidden p-0 shadow-lg sm:max-w-xl">
		<Dialog.Header class="sr-only">
			<Dialog.Title>Search</Dialog.Title>
			<Dialog.Description>Assets, searches and commands</Dialog.Description>
		</Dialog.Header>
		<Command.Root shouldFilter={false} class="[&_[data-cmd-input-wrapper]]:border-b">
			<Command.Input
				bind:value={raw}
				placeholder="Search a value, run a query, or type {COMMAND_PREFIX} for commands"
			/>
			<Command.List class="max-h-none overflow-visible">
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[24rem]">
					{#if searching && !commandMode && term.length >= 2 && !searchResults.length && !validValue}
						<div class="flex flex-col gap-2 p-2" aria-busy="true">
							{#each Array(3) as _, i (i)}
								<div class="flex items-center gap-2 px-2 py-1.5">
									<Skeleton class="size-4 shrink-0 rounded" />
									<Skeleton class="h-3.5 {i % 2 ? 'w-40' : 'w-56'} max-w-full" />
								</div>
							{/each}
						</div>
					{/if}

					{#if showRecents}
						{#if visits.length}
							<Command.Group heading="Recent">
								{#each visits as visit (visit.kind + visit.id)}
									<Command.Item
										value="visit:{visit.id}"
										onSelect={() =>
											run(() =>
												goto(
													visit.kind === 'scan' ? ROUTES.scan(visit.id) : ROUTES.target(visit.id)
												)
											)}
									>
										{#if visit.kind === 'scan'}
											<Radar class="h-4 w-4 shrink-0" />
										{:else}
											<Crosshair class="h-4 w-4 shrink-0" />
										{/if}
										<span class="truncate">{visit.label}</span>
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}
						{#if searches.length}
							<Command.Group heading="Recent searches">
								{#each searches as entry (entry.dimension + entry.query)}
									{@const spec = SURFACE[entry.dimension]}
									<Command.Item
										value="search:{entry.dimension}:{entry.query}"
										onSelect={() =>
											run(() => goto(searchHref(entry.dimension, entry.query, scope, 'project')))}
									>
										<spec.icon class="h-4 w-4 shrink-0" />
										<span class="truncate font-mono text-xs">{entry.query}</span>
										<Command.Shortcut>{spec.label}</Command.Shortcut>
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}
						{#if starters.length}
							<Command.Group heading="Commands">
								{#each starters as command (command.id)}
									<Command.Item value={command.id} onSelect={() => run(command.run)}>
										<command.icon class="h-4 w-4 shrink-0" />
										<span class="truncate">{command.label}</span>
										{#if command.hint}
											<Command.Shortcut class="truncate">{command.hint}</Command.Shortcut>
										{/if}
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}
					{/if}

					{#if !commandMode && term}
						{#if searchResults.length}
							<Command.Group heading="Targets">
								{#each searchResults as t (t.id)}
									<Command.Item
										value="target:{t.id}"
										onSelect={() => run(() => goto(ROUTES.target(t.id)))}
									>
										<Crosshair class="h-4 w-4 shrink-0" />
										<span class="truncate">{t.target_value}</span>
										<Command.Shortcut>{t.target_type}</Command.Shortcut>
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}

						{#if isCve(term) || lookups.length}
							<Command.Group heading="Find">
								{#if isCve(term)}
									<Command.Item
										value="cve:page"
										onSelect={() => run(() => goto(ROUTES.cve(cveId(term))))}
									>
										<ShieldAlert class="h-4 w-4 shrink-0" />
										<span class="truncate">{cveId(term)}</span>
										<Command.Shortcut>Exposure</Command.Shortcut>
									</Command.Item>
								{/if}
								{#each lookups as lookup (lookup.dimension + lookup.query)}
									{@const spec = SURFACE[lookup.dimension]}
									<Command.Item
										value="find:{lookup.dimension}:{lookup.query}"
										onSelect={() =>
											run(() => goto(searchHref(lookup.dimension, lookup.query, scope, 'project')))}
									>
										<spec.icon class="h-4 w-4 shrink-0" />
										<span class="truncate">{spec.label}</span>
										<Command.Shortcut class="truncate font-mono">{lookup.query}</Command.Shortcut>
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}

						{#if queryMatches.length}
							<Command.Group heading="Search">
								{#each queryMatches as match (match.dimension)}
									{@const spec = SURFACE[match.dimension]}
									{#if scope.kind !== 'project'}
										<Command.Item
											value="query:here:{match.dimension}"
											onSelect={() =>
												run(() => goto(searchHref(match.dimension, term, scope, 'here')))}
										>
											<spec.icon class="h-4 w-4 shrink-0" />
											<span class="truncate">{spec.label}</span>
											<Command.Shortcut class="truncate">{scope.label}</Command.Shortcut>
										</Command.Item>
									{/if}
									<Command.Item
										value="query:project:{match.dimension}"
										onSelect={() =>
											run(() => goto(searchHref(match.dimension, term, scope, 'project')))}
									>
										<spec.icon class="h-4 w-4 shrink-0" />
										<span class="truncate">{spec.label}</span>
										<Command.Shortcut class="truncate">{activeProject?.name ?? ''}</Command.Shortcut
										>
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}

						{#if askReady && isQuestion(term)}
							<Command.Group heading="Ask">
								<Command.Item
									value="ask:{term}"
									onSelect={() => run(() => goto(ROUTES.ask({ q: term })))}
								>
									<Sparkles class="h-4 w-4 shrink-0 text-primary" />
									<span class="truncate">{term}</span>
									<Command.Shortcut>Ask</Command.Shortcut>
								</Command.Item>
							</Command.Group>
						{/if}

						{#if validValue}
							<Command.Group heading="Run">
								<Command.Item
									value="scan:{validValue}"
									onSelect={() => run(() => onScan(validValue ?? undefined))}
								>
									<Play class="h-4 w-4 shrink-0" />
									<span class="truncate">Start scan</span>
									<Command.Shortcut class="truncate font-mono">{validValue}</Command.Shortcut>
								</Command.Item>
								<Command.Item
									value="toolbox:{validValue}"
									onSelect={() => run(() => onToolbox(validValue ?? ''))}
								>
									<TOOLBOX_ICON class="h-4 w-4 shrink-0" />
									<span class="truncate">Open in Toolbox</span>
									<Command.Shortcut class="truncate font-mono">{validValue}</Command.Shortcut>
								</Command.Item>
							</Command.Group>
						{/if}

						{#if matched.length}
							<Command.Group heading="Commands">
								{#each matched.slice(0, MAX_COMMANDS) as command (command.id)}
									<Command.Item value={command.id} onSelect={() => run(command.run)}>
										<command.icon class="h-4 w-4 shrink-0" />
										<span class="truncate">{command.label}</span>
										{#if command.hint}
											<Command.Shortcut class="truncate">{command.hint}</Command.Shortcut>
										{/if}
									</Command.Item>
								{/each}
							</Command.Group>
						{/if}

						{#if !searching && !searchResults.length && !lookups.length && !queryMatches.length && !matched.length && !validValue}
							<div class="py-6 text-center text-sm text-muted-foreground">Nothing matches</div>
						{/if}
					{/if}

					{#if commandMode}
						{#each grouped as entry (entry.group)}
							<Command.Group heading={GROUP_LABELS[entry.group]}>
								{#each entry.items as command (command.id)}
									<Command.Item value={command.id} onSelect={() => run(command.run)}>
										<command.icon class="h-4 w-4 shrink-0" />
										<span class="truncate">{command.label}</span>
										{#if command.hint}
											<Command.Shortcut class="truncate">{command.hint}</Command.Shortcut>
										{/if}
									</Command.Item>
								{/each}
							</Command.Group>
						{/each}
						{#if !grouped.length}
							<div class="py-6 text-center text-sm text-muted-foreground">No command matches</div>
						{/if}
					{/if}
				</ScrollArea>
			</Command.List>

			<div
				class="flex items-center gap-3 border-t px-3 py-2 text-2xs text-muted-foreground"
				data-palette-legend
			>
				<span class="flex items-center gap-1">
					<kbd class="rounded border bg-muted px-1 font-mono">{COMMAND_PREFIX}</kbd>
					Commands
				</span>
				<span class="flex items-center gap-1">
					<kbd class="rounded border bg-muted px-1 font-mono">↵</kbd>
					Open
				</span>
				<span class="ml-auto flex items-center gap-1">
					<kbd class="rounded border bg-muted px-1 font-mono">{IS_MAC ? '⌘⇧K' : 'Ctrl+Shift+K'}</kbd
					>
					Toolbox
				</span>
			</div>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={!!cancelTarget}
	title="Cancel scan"
	description="The scan stops and is marked cancelled."
	confirmLabel="Cancel scan"
	cancelLabel="Keep running"
	destructive
	loading={cancelling}
	loadingLabel="Cancelling"
	onOpenChange={(o) => !o && (cancelTarget = null)}
	onConfirm={confirmCancel}
/>

<ConfirmDialog
	open={cancelAllOpen}
	title="Cancel all unfinished scans"
	description="Running, queued and paused scans stop and are marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep"
	destructive
	loading={cancelling}
	loadingLabel="Cancelling"
	onOpenChange={(o) => (cancelAllOpen = o)}
	onConfirm={confirmCancelAll}
/>
