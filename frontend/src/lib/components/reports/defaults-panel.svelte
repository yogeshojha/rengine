<script lang="ts">
	import { untrack } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { SELECT_NONE } from '$lib/constants';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import BrandingPanel from '$lib/components/reports/builder/branding-panel.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { toast } from 'svelte-sonner';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import type { ReportBranding, ReportDefaults } from '$lib/types/report';

	interface Props {
		onDirtyChange?: (dirty: boolean) => void;
	}

	let { onDirtyChange }: Props = $props();

	let defaults = $state<ReportDefaults | null>(null);
	let branding = $state<ReportBranding | null>(null);
	let theme = $state('');
	let snapshot = $state('');
	let saving = $state(false);
	let loading = $state(true);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const selectedTheme = $derived(reportCatalog.themes.find((t) => t.slug === theme));
	const dirty = $derived(Boolean(branding) && JSON.stringify({ branding, theme }) !== snapshot);

	$effect(() => onDirtyChange?.(dirty));

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!dirty || saving || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	$effect(() => {
		if (typeof window === 'undefined') return;
		function onBeforeUnload(e: BeforeUnloadEvent) {
			if (!dirty || saving) return;
			e.preventDefault();
		}
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});

	$effect(() => {
		untrack(() => {
			void reportCatalog.fetch();
			reportsApi
				.defaults()
				.then((value) => {
					defaults = value;
					branding = {
						...value.branding,
						distribution: [...value.branding.distribution],
						revisions: value.branding.revisions.map((r) => ({ ...r }))
					};
					theme = value.theme;
					snapshot = JSON.stringify({ branding, theme });
				})
				.catch((e) => toast.error(e instanceof Error ? e.message : 'Branding not loaded'))
				.finally(() => (loading = false));
		});
	});

	async function save() {
		if (!branding || !defaults) return;
		saving = true;
		try {
			const saved = await reportsApi.saveDefaults({
				...defaults,
				branding,
				theme
			});
			defaults = saved;
			snapshot = JSON.stringify({ branding, theme });
			toast.success('Branding saved');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Branding not saved');
		} finally {
			saving = false;
		}
	}
</script>

{#if loading}
	<Skeleton class="h-64 w-full" />
{:else if branding}
	<div class="space-y-5">
		<Card.Root class="gap-0 py-0">
			<PanelHead title="Theme" description="Applied when a template sets none">
				{#if !isAdmin}Read-only{/if}
			</PanelHead>
			<div class="px-5 py-4">
				<Select.Root
					type="single"
					value={theme || SELECT_NONE}
					onValueChange={(v) => (theme = v === SELECT_NONE ? '' : v)}
					disabled={!isAdmin}
				>
					<Select.Trigger class="w-full sm:w-72" aria-label="Theme">
						{#if selectedTheme}
							<span class="flex items-center gap-2">
								<span class="size-3 rounded-full border" style="background:{selectedTheme.accent}"
								></span>
								{selectedTheme.name}
							</span>
						{:else}
							None
						{/if}
					</Select.Trigger>
					<Select.Content class="max-h-72">
						<Select.Item value={SELECT_NONE} label="None">None</Select.Item>
						{#each reportCatalog.themes as option (option.slug)}
							<Select.Item value={option.slug} label={option.name}>
								<span class="size-3 rounded-full border" style="background:{option.accent}"></span>
								{option.name}
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead title="Branding" description="Applied to fields a template leaves empty">
				{#if !isAdmin}Read-only{/if}
			</PanelHead>
			<fieldset class="px-5 py-5" disabled={!isAdmin}>
				<BrandingPanel bind:branding />
			</fieldset>
		</Card.Root>

		<div class="flex items-center justify-end gap-3">
			{#if dirty}<span class="text-xs text-muted-foreground">Unsaved changes</span>{/if}
			<Button
				variant="outline"
				disabled={!dirty}
				onclick={() => {
					const previous = JSON.parse(snapshot);
					branding = previous.branding;
					theme = previous.theme;
				}}
			>
				Discard
			</Button>
			<LoadingButton loading={saving} disabled={!isAdmin || !dirty} onclick={save}
				>Save</LoadingButton
			>
		</div>
	</div>
{/if}

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	onOpenChange={(open) => {
		showLeaveDialog = open;
		if (!open) pendingNav = null;
	}}
	onConfirm={() => {
		const go = pendingNav;
		pendingNav = null;
		go?.();
	}}
/>
