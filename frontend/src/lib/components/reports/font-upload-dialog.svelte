<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import type { FontFaceUpload } from '$lib/types/report';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	const WEIGHTS = [100, 200, 300, 400, 500, 600, 700, 800, 900];
	const ROLES = [
		{ key: 'sans', label: 'Sans' },
		{ key: 'serif', label: 'Serif' },
		{ key: 'mono', label: 'Monospaced' }
	];

	let name = $state('');
	let role = $state('sans');
	let note = $state('');
	let faces = $state<(FontFaceUpload & { size: number })[]>([]);
	let busy = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

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
		if (!name.trim()) {
			toast.error('Give the typeface a name.');
			return;
		}
		if (!faces.length) {
			toast.error('Add at least one font file.');
			return;
		}
		busy = true;
		try {
			const family = await reportsApi.uploadFont({
				name: name.trim(),
				role,
				note: note.trim(),
				faces: faces.map(({ filename, content, weight, italic }) => ({
					filename,
					content,
					weight,
					italic
				}))
			});
			toast.success(`${family.name} is available to every theme`);
			await reportCatalog.fetch(true);
			open = false;
			name = '';
			note = '';
			faces = [];
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'That typeface could not be stored');
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="flex max-h-[92vh] flex-col gap-0 p-0 sm:max-w-2xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Upload a typeface</Dialog.Title>
			<Dialog.Description>
				Files are read from disk and stored on this instance. A report never fetches a font from the
				internet.
			</Dialog.Description>
		</Dialog.Header>

		<ScrollArea
			class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-13rem)]"
		>
			<div class="space-y-5 px-6 py-5">
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="space-y-1.5">
						<Label class="text-xs" for="font-name">Family name</Label>
						<Input id="font-name" bind:value={name} placeholder="Acme Grotesk" class="h-9" />
						<p class="text-xs text-muted-foreground">This is the name a theme refers to.</p>
					</div>
					<div class="space-y-1.5">
						<Label class="text-xs">Offer it for</Label>
						<Select.Root type="single" bind:value={role}>
							<Select.Trigger class="h-9 w-full">
								{ROLES.find((r) => r.key === role)?.label}
							</Select.Trigger>
							<Select.Content>
								{#each ROLES as item (item.key)}
									<Select.Item value={item.key}>{item.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				</div>

				<div class="space-y-1.5">
					<Label class="text-xs" for="font-note">Note</Label>
					<Input
						id="font-note"
						bind:value={note}
						placeholder="Licensed for client deliverables"
						class="h-9"
					/>
				</div>

				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<Label class="text-xs">Faces</Label>
						<Button variant="outline" size="sm" onclick={() => fileInput?.click()}>
							<UploadIcon class="mr-1.5 size-3.5" />
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
						<div class="overflow-hidden rounded-md border">
							{#each faces as face, index (index)}
								<div class="flex items-center gap-3 border-b px-3 py-2 last:border-b-0">
									<span class="min-w-0 flex-1 truncate font-mono text-xs">{face.filename}</span>
									<span class="shrink-0 text-xs text-muted-foreground">
										{(face.size / 1024).toFixed(0)} KB
									</span>
									<Select.Root
										type="single"
										value={String(face.weight)}
										onValueChange={(v) => v && (faces[index].weight = Number(v))}
									>
										<Select.Trigger class="h-8 w-20 shrink-0">{face.weight}</Select.Trigger>
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
										/>
									</div>
									<Button
										variant="ghost"
										size="icon"
										class="size-7 shrink-0 text-destructive"
										onclick={() => (faces = faces.filter((_, i) => i !== index))}
										aria-label="Remove"
									>
										<Trash2Icon class="size-3.5" />
									</Button>
								</div>
							{/each}
						</div>
						<p class="text-xs text-muted-foreground">
							The weight and italic flag are read from each filename. Correct them here if they are
							wrong.
						</p>
					{:else}
						<p
							class="rounded-md border border-dashed px-3 py-6 text-center text-xs text-muted-foreground"
						>
							WOFF2, WOFF, TrueType or OpenType. Add one file per weight.
						</p>
					{/if}
				</div>
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
			<LoadingButton loading={busy} onclick={upload}>Upload</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
