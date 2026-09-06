<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import { toast } from 'svelte-sonner';
	import type { ReportBranding } from '$lib/types/report';

	let { branding = $bindable() }: { branding: ReportBranding } = $props();

	const MAX_LOGO = 512_000;
	let logoInput = $state<HTMLInputElement | null>(null);
	let distributionDraft = $state('');

	async function pickLogo(event: Event) {
		const file = (event.target as HTMLInputElement).files?.[0];
		if (!file) return;
		if (file.size > MAX_LOGO) {
			toast.error('Choose a logo under 500 KB.');
			return;
		}
		branding.company_logo = await new Promise<string>((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result));
			reader.onerror = reject;
			reader.readAsDataURL(file);
		});
	}

	function addRecipient() {
		const value = distributionDraft.trim();
		if (!value) return;
		branding.distribution = [...branding.distribution, value];
		distributionDraft = '';
	}

	function addRevision() {
		branding.revisions = [
			...branding.revisions,
			{ version: '', date: new Date().toISOString().slice(0, 10), author: '', note: '' }
		];
	}
</script>

<div class="space-y-6">
	<div class="space-y-2">
		<Label class="text-xs">Logo</Label>
		<div class="flex items-center gap-3">
			{#if branding.company_logo}
				<img
					src={branding.company_logo}
					alt=""
					class="h-10 max-w-40 rounded border bg-white object-contain p-1"
				/>
			{/if}
			<Button variant="outline" size="sm" onclick={() => logoInput?.click()}>
				<UploadIcon class="mr-1.5 size-3.5" />
				{branding.company_logo ? 'Replace' : 'Upload'}
			</Button>
			{#if branding.company_logo}
				<Button
					variant="ghost"
					size="sm"
					class="text-destructive"
					onclick={() => (branding.company_logo = '')}
				>
					Remove
				</Button>
			{/if}
			<input
				bind:this={logoInput}
				type="file"
				accept="image/png,image/jpeg,image/svg+xml,image/webp"
				class="hidden"
				onchange={pickLogo}
			/>
		</div>
		<p class="text-xs text-muted-foreground">PNG, JPEG, SVG or WebP, under 500 KB.</p>
	</div>

	<div class="grid gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Label class="text-xs">Your company</Label>
			<Input bind:value={branding.company_name} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Client</Label>
			<Input bind:value={branding.client_name} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Prepared for</Label>
			<Input bind:value={branding.prepared_for} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Prepared by</Label>
			<Input bind:value={branding.prepared_by} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Author</Label>
			<Input bind:value={branding.author} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Classification</Label>
			<Input bind:value={branding.classification} placeholder="Confidential" class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Document reference</Label>
			<Input bind:value={branding.document_id} placeholder="RNG-2026-0001" class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Version</Label>
			<Input bind:value={branding.version} placeholder="1.0" class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Contact email</Label>
			<Input bind:value={branding.contact_email} class="h-9" />
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Contact URL</Label>
			<Input bind:value={branding.contact_url} class="h-9" />
		</div>
	</div>

	<Separator />

	<div class="space-y-2">
		<Label class="text-xs">Distribution list</Label>
		<div class="flex gap-2">
			<Input
				bind:value={distributionDraft}
				placeholder="Name or role"
				class="h-9"
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
			/>
			<Button variant="outline" size="sm" onclick={addRecipient}>Add</Button>
		</div>
		{#if branding.distribution.length}
			<div class="flex flex-wrap gap-1.5">
				{#each branding.distribution as name, index (index)}
					<span class="flex items-center gap-1 rounded-md border px-2 py-1 text-xs">
						{name}
						<button
							type="button"
							class="text-muted-foreground hover:text-destructive"
							onclick={() =>
								(branding.distribution = branding.distribution.filter((_, i) => i !== index))}
							aria-label="Remove"
						>
							×
						</button>
					</span>
				{/each}
			</div>
		{/if}
	</div>

	<div class="space-y-2">
		<div class="flex items-center justify-between">
			<Label class="text-xs">Revision history</Label>
			<Button variant="ghost" size="sm" class="h-7 text-xs" onclick={addRevision}>
				<PlusIcon class="mr-1 size-3" />
				Add a row
			</Button>
		</div>
		{#each branding.revisions as revision, index (index)}
			<div class="flex gap-2">
				<Input bind:value={revision.version} placeholder="1.0" class="h-9 w-20" />
				<Input bind:value={revision.date} placeholder="2026-09-06" class="h-9 w-32" />
				<Input bind:value={revision.author} placeholder="Author" class="h-9 w-36" />
				<Input bind:value={revision.note} placeholder="What changed" class="h-9 flex-1" />
				<Button
					variant="ghost"
					size="icon"
					class="size-9 shrink-0 text-destructive"
					onclick={() => (branding.revisions = branding.revisions.filter((_, i) => i !== index))}
					aria-label="Remove"
				>
					<Trash2Icon class="size-3.5" />
				</Button>
			</div>
		{/each}
	</div>

	<Separator />

	<div class="space-y-1.5">
		<Label class="text-xs">Confidentiality statement</Label>
		<Textarea bind:value={branding.confidentiality_statement} rows={3} class="text-sm" />
	</div>
	<div class="space-y-1.5">
		<Label class="text-xs">Disclaimer</Label>
		<Textarea bind:value={branding.disclaimer} rows={3} class="text-sm" />
	</div>
</div>
