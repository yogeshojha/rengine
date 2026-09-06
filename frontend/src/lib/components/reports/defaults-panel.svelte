<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import InfoIcon from '@lucide/svelte/icons/info';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import BrandingPanel from '$lib/components/reports/builder/branding-panel.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { toast } from 'svelte-sonner';
	import type { ReportBranding, ReportDefaults } from '$lib/types/report';

	let defaults = $state<ReportDefaults | null>(null);
	let branding = $state<ReportBranding | null>(null);
	let theme = $state('');
	let snapshot = $state('');
	let saving = $state(false);
	let loading = $state(true);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const dirty = $derived(Boolean(branding) && JSON.stringify({ branding, theme }) !== snapshot);

	$effect(() => {
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
			.catch((e) => toast.error(e instanceof Error ? e.message : 'Defaults could not be loaded'))
			.finally(() => (loading = false));
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
			toast.success('Saved. New reports start from this.');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Defaults could not be saved');
		} finally {
			saving = false;
		}
	}
</script>

{#if loading}
	<Skeleton class="h-64 w-full" />
{:else if branding}
	<div class="space-y-5">
		<Alert.Root>
			<InfoIcon />
			<Alert.Title>Defaults fill what a template leaves blank</Alert.Title>
			<Alert.Description>
				The logo, company and classification set here apply to every template. A template that sets
				its own value takes precedence.
			</Alert.Description>
		</Alert.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead title="Default theme" description="Used when a template does not name one">
				{#if !isAdmin}Read only{/if}
			</PanelHead>
			<div class="px-5 py-4">
				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-md border px-2.5 py-1.5 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
						data-active={theme === ''}
						disabled={!isAdmin}
						onclick={() => (theme = '')}
					>
						No default
					</button>
					{#each reportCatalog.themes as option (option.slug)}
						<button
							type="button"
							class="flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
							data-active={theme === option.slug}
							disabled={!isAdmin}
							onclick={() => (theme = option.slug)}
						>
							<span class="size-3.5 rounded-full border" style="background:{option.accent}"></span>
							{option.name}
						</button>
					{/each}
				</div>
			</div>
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="Default branding"
				description="Applied to every report that leaves a field empty"
			/>
			<div class="px-5 py-5" class:pointer-events-none={!isAdmin} class:opacity-70={!isAdmin}>
				<BrandingPanel bind:branding />
			</div>
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
