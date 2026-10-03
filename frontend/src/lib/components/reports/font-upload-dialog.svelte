<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { catalogLabel } from '$lib/config/reports';
	import { formatBytes } from '$lib/utilities/format';
	import type { FontFaceUpload } from '$lib/types/report';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	const WEIGHTS = [100, 200, 300, 400, 500, 600, 700, 800, 900];
	const DEFAULT_ROLE = 'sans';
	const ROLES = $derived(reportCatalog.catalog?.font_roles ?? []);

	let name = $state('');
	let role = $state(DEFAULT_ROLE);
	let note = $state('');
	let faces = $state<(FontFaceUpload & { filename: string; size: number })[]>([]);
	let busy = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

	const dirty = $derived(
		name.trim() !== '' || note.trim() !== '' || role !== DEFAULT_ROLE || faces.length > 0
	);
	const ready = $derived(name.trim() !== '' && faces.length > 0);

	function reset() {
		name = '';
		role = DEFAULT_ROLE;
		note = '';
		faces = [];
	}

	const guard = new DiscardGuard(
		() => dirty,
		() => {
			reset();
			open = false;
		}
	);

	function requestOpen(next: boolean) {
		if (next) open = true;
		else if (!busy) guard.close();
	}

	function guessWeight(filename: string): number {
		const lower = filename.toLowerCase();
		const table: [string, number][] = [
			['thin', 100],
			['extralight', 200],
			['ultralight', 200],
			['light', 300],
			['medium', 500],
			['semibold', 600],
			['demibold', 600],
			['extrabold', 800],
			['ultrabold', 800],
			['black', 900],
			['heavy', 900],
			['bold', 700]
		];
		for (const [needle, weight] of table) if (lower.includes(needle)) return weight;
		const digits = lower.match(/[-_](\d00)\b/);
		return digits ? Number(digits[1]) : 400;
	}

	async function pick(event: Event) {
		const chosen = Array.from((event.target as HTMLInputElement).files ?? []);
		for (const file of chosen) {
			const buffer = await file.arrayBuffer();
			let binary = '';
			const bytes = new Uint8Array(buffer);
			for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
			faces = [
				...faces,
				{
					filename: file.name,
					content: btoa(binary),
					weight: guessWeight(file.name),
					italic: /italic|oblique/i.test(file.name),
					size: file.size
				}
			];
		}
		if (!name && chosen.length) {
			name = chosen[0].name.replace(/\.[^.]+$/, '').replace(/[-_](regular|400).*$/i, '');
		}
		(event.target as HTMLInputElement).value = '';
	}

	async function upload() {
		if (!ready) return;
		busy = true;
		try {
			const family = await reportsApi.uploadFont({
				name: name.trim(),
				role,
				note: note.trim(),
				faces: faces.map(({ content, weight, italic }) => ({ content, weight, italic }))
			});
			toast.success(`${family.name} uploaded`);
			await reportCatalog.fetch(true);
			open = false;
			reset();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Typeface not uploaded');
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open={() => open, requestOpen}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Upload a typeface</Dialog.Title>
		</Dialog.Header>

		<ScrollArea
			class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-13rem)]"
		>
			<div class="flex flex-col gap-4 px-6 py-5">
				<div class="grid gap-4 sm:grid-cols-2">
					<FormField label="Family name">
						{#snippet children({ id })}
							<Input {id} bind:value={name} placeholder="Acme Grotesk" class="h-9" />
						{/snippet}
					</FormField>
					<FormField label="Role">
						{#snippet children({ id })}
							<Select.Root type="single" bind:value={role}>
								<Select.Trigger {id} class="h-9 w-full">
									{catalogLabel(ROLES, role)}
								</Select.Trigger>
								<Select.Content>
									{#each ROLES as item (item.key)}
										<Select.Item value={item.key}>{item.label}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						{/snippet}
					</FormField>
				</div>

				<FormField label="Note">
					{#snippet children({ id })}
						<Input
							{id}
							bind:value={note}
							placeholder="Licensed for client deliverables"
							class="h-9"
						/>
					{/snippet}
				</FormField>

				<div class="space-y-3">
					<div class="flex items-center justify-between">
						<Label>Faces</Label>
						<Button variant="outline" size="sm" onclick={() => fileInput?.click()}>
							<UploadIcon class="size-3.5" />
							Add files
						</Button>
						<input
							bind:this={fileInput}
							type="file"
							multiple
							accept=".woff2,.woff,.ttf,.otf,font/woff2,font/woff,font/ttf,font/otf"
							class="hidden"
							onchange={pick}
						/>
					</div>

					{#if faces.length}
						<div class="overflow-hidden rounded-lg border">
							{#each faces as face, index (index)}
								<div class="flex items-center gap-3 border-b px-3 py-2 last:border-b-0">
									<span class="min-w-0 flex-1 truncate font-mono text-xs">{face.filename}</span>
									<span class="shrink-0 text-xs text-muted-foreground">
										{formatBytes(face.size)}
									</span>
									<Select.Root
										type="single"
										value={String(face.weight)}
										onValueChange={(v) => v && (faces[index].weight = Number(v))}
									>
										<Select.Trigger class="h-8 w-20 shrink-0" aria-label="Weight of {face.filename}"
											>{face.weight}</Select.Trigger
										>
										<Select.Content>
											{#each WEIGHTS as weight (weight)}
												<Select.Item value={String(weight)}>{weight}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
									<div class="flex shrink-0 items-center gap-1.5">
										<span class="text-xs text-muted-foreground">Italic</span>
										<Switch
											checked={face.italic}
											onCheckedChange={(v) => (faces[index].italic = v)}
											aria-label="Italic {face.filename}"
										/>
									</div>
									<Button
										variant="ghost"
										size="icon-sm"
										class="shrink-0 text-destructive"
										onclick={() => (faces = faces.filter((_, i) => i !== index))}
										aria-label="Remove {face.filename}"
									>
										<Trash2Icon class="size-3.5" />
									</Button>
								</div>
							{/each}
						</div>
						<p class="text-xs text-muted-foreground">
							Weight and italic are read from the filename.
						</p>
					{:else}
						<p
							class="rounded-lg border border-dashed px-3 py-6 text-center text-xs text-muted-foreground"
						>
							WOFF2, WOFF, TrueType or OpenType, one file per weight.
						</p>
					{/if}
				</div>
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" disabled={busy} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={busy} loadingLabel="Uploading" disabled={!ready} onclick={upload}
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
