<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import YamlEditor from '$lib/components/yaml-editor.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import { toast } from 'svelte-sonner';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	const SAMPLE = `key: house-style
name: House style
description: House style for client deliverables.
author: Security team
color:
  page: "#ffffff"
  ink: "#141414"
  accent: "#0f5132"
  accent_soft: "#e7f2ec"
  severity:
    critical: "#b02a37"
    high: "#c2670a"
  chart: ["#0f5132", "#1c6b8c", "#7a4fb0", "#b8860b", "#0f7b7b"]
type:
  heading: source-serif
  body: inter
  mono: ibm-plex-mono
  base_size: 9.5
  scale: 1.22
layout:
  table: boxed
  finding: card
  heading: numbered
cover:
  layout: band
  art: none
  ink: light
  background: "#0f5132"
css: |
  .section__title { letter-spacing: -0.01em; }
`;

	let content = $state('');
	let busy = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

	const dirty = $derived(content.trim() !== '');

	const guard = new DiscardGuard(
		() => dirty,
		() => {
			content = '';
			open = false;
		}
	);

	function requestOpen(next: boolean) {
		if (next) open = true;
		else if (!busy) guard.close();
	}

	async function pick(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		content = await file.text();
	}

	async function upload() {
		if (!dirty) return;
		busy = true;
		try {
			const theme = await reportsApi.uploadTheme(content);
			toast.success(`${theme.name} uploaded`);
			await reportCatalog.fetch(true);
			open = false;
			content = '';
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Theme not uploaded');
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open={() => open, requestOpen}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Upload a theme</Dialog.Title>
			<Dialog.Description>
				A YAML file of design tokens. Omitted tokens keep their defaults.
			</Dialog.Description>
		</Dialog.Header>
		<ScrollArea
			class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-13rem)]"
		>
			<div class="flex flex-col gap-4 px-6 py-5">
				<div class="flex items-center gap-2">
					<Button variant="outline" size="sm" onclick={() => fileInput?.click()}>
						<UploadIcon class="size-3.5" />
						Choose a file
					</Button>
					<Button variant="ghost" size="sm" onclick={() => (content = SAMPLE)}>Load example</Button>
					<input
						bind:this={fileInput}
						type="file"
						accept=".yaml,.yml,text/yaml"
						class="hidden"
						onchange={pick}
					/>
				</div>
				<div class="space-y-3">
					<Label>Theme file</Label>
					<div class="h-[26rem] overflow-hidden rounded-md border">
						<YamlEditor
							value={content}
							completions={false}
							filename="theme.yaml"
							placeholder="key: my-theme"
							onChange={(next) => (content = next)}
						/>
					</div>
				</div>
			</div>
		</ScrollArea>
		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" disabled={busy} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={busy} loadingLabel="Uploading" disabled={!dirty} onclick={upload}
				>Upload</LoadingButton
			>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
