<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import XIcon from '@lucide/svelte/icons/x';
	import { toast } from 'svelte-sonner';
	import type { ReportBranding } from '$lib/types/report';

	let { branding = $bindable() }: { branding: ReportBranding } = $props();

	const MAX_LOGO = 512_000;
	let logoInput = $state<HTMLInputElement | null>(null);
	let distributionDraft = $state('');

	async function pickLogo(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		if (file.size > MAX_LOGO) {
			toast.error('Logo exceeds 500 KB. Choose a smaller file.');
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
		if (!value || branding.distribution.includes(value)) return;
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

{#snippet group(title: string)}
	<h3 class="text-sm font-medium">{title}</h3>
{/snippet}

<div class="space-y-6">
	<section class="space-y-4">
		{@render group('Organization')}
		<div class="flex flex-wrap items-center gap-3">
			<div
				class="flex h-14 w-40 items-center justify-center rounded-md border border-dashed bg-muted/30"
			>
				{#if branding.company_logo}
					<img src={branding.company_logo} alt="Logo" class="max-h-12 max-w-36 object-contain" />
				{:else}
					<span class="text-xs text-muted-foreground">No logo</span>
				{/if}
			</div>
			<div class="flex flex-col gap-1">
				<div class="flex gap-2">
					<Button variant="outline" size="sm" onclick={() => logoInput?.click()}>
						<UploadIcon class="mr-1.5 size-3.5" />
						{branding.company_logo ? 'Replace logo' : 'Upload logo'}
					</Button>
					{#if branding.company_logo}
						<Button variant="ghost" size="sm" onclick={() => (branding.company_logo = '')}>
							Remove
						</Button>
					{/if}
				</div>
				<span class="text-xs text-muted-foreground">PNG, JPEG, SVG or WebP. 500 KB maximum.</span>
			</div>
			<input
				bind:this={logoInput}
				type="file"
				accept="image/png,image/jpeg,image/svg+xml,image/webp"
				class="hidden"
				onchange={pickLogo}
			/>
		</div>
		<div class="grid gap-4 sm:grid-cols-3">
			<FormField label="Company name">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.company_name} class="h-9" />
				{/snippet}
			</FormField>
			<FormField label="Contact email">
				{#snippet children({ id })}
					<Input {id} type="email" bind:value={branding.contact_email} class="h-9" />
				{/snippet}
			</FormField>
			<FormField label="Website">
				{#snippet children({ id })}
					<Input
						{id}
						type="url"
						bind:value={branding.contact_url}
						placeholder="https://"
						class="h-9"
					/>
				{/snippet}
			</FormField>
		</div>
	</section>

	<Separator />

	<section class="space-y-4">
		{@render group('Engagement')}
		<div class="grid gap-4 sm:grid-cols-2">
			<FormField label="Client name">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.client_name} class="h-9" />
				{/snippet}
			</FormField>
			<FormField label="Prepared for">
				{#snippet children({ id })}
					<Input
						{id}
						bind:value={branding.prepared_for}
						placeholder={branding.client_name || 'Client name'}
						class="h-9"
					/>
				{/snippet}
			</FormField>
			<FormField label="Prepared by">
				{#snippet children({ id })}
					<Input
						{id}
						bind:value={branding.prepared_by}
						placeholder={branding.company_name || 'Company name'}
						class="h-9"
					/>
				{/snippet}
			</FormField>
			<FormField label="Author">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.author} class="h-9" />
				{/snippet}
			</FormField>
		</div>
	</section>

	<Separator />

	<section class="space-y-4">
		{@render group('Document')}
		<div class="grid gap-4 sm:grid-cols-3">
			<FormField label="Classification">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.classification} placeholder="Confidential" class="h-9" />
				{/snippet}
			</FormField>
			<FormField label="Reference">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.document_id} placeholder="RNG-2026-0001" class="h-9" />
				{/snippet}
			</FormField>
			<FormField label="Version">
				{#snippet children({ id })}
					<Input {id} bind:value={branding.version} placeholder="1.0" class="h-9" />
				{/snippet}
			</FormField>
		</div>

		<FormField label="Distribution list">
			{#snippet children({ id })}
				<div class="space-y-2">
					<div class="flex gap-2">
						<Input
							{id}
							bind:value={distributionDraft}
							placeholder="Name or role"
							class="h-9"
							onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
						/>
						<Button
							variant="outline"
							size="sm"
							class="h-9"
							disabled={!distributionDraft.trim()}
							onclick={addRecipient}
						>
							Add
						</Button>
					</div>
					{#if branding.distribution.length}
						<div class="flex flex-wrap gap-1.5">
							{#each branding.distribution as name, index (index)}
								<Badge variant="outline" class="gap-1 pr-1 text-xs font-normal">
									{name}
									<button
										type="button"
										class="rounded-sm text-muted-foreground hover:text-foreground"
										onclick={() =>
											(branding.distribution = branding.distribution.filter((_, i) => i !== index))}
										aria-label="Remove {name}"
									>
										<XIcon class="size-3" />
									</button>
								</Badge>
							{/each}
						</div>
					{/if}
				</div>
			{/snippet}
		</FormField>

		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<span class="text-sm font-medium">Revision history</span>
				<Button variant="outline" size="sm" class="h-8" onclick={addRevision}>
					<PlusIcon class="mr-1 size-3.5" />
					Add revision
				</Button>
			</div>
			{#if branding.revisions.length}
				<div class="rounded-md border">
					<div
						class="hidden grid-cols-[5rem_9rem_10rem_minmax(0,1fr)_2.25rem] gap-2 border-b bg-muted/30 px-2 py-1.5 text-2xs font-medium text-muted-foreground uppercase sm:grid"
					>
						<span>Version</span>
						<span>Date</span>
						<span>Author</span>
						<span>Change</span>
						<span></span>
					</div>
					{#each branding.revisions as revision, index (index)}
						<div
							class="grid grid-cols-2 gap-2 border-b p-2 last:border-b-0 sm:grid-cols-[5rem_9rem_10rem_minmax(0,1fr)_2.25rem]"
						>
							<Input
								bind:value={revision.version}
								placeholder="1.0"
								class="h-9"
								aria-label="Version"
							/>
							<Input type="date" bind:value={revision.date} class="h-9" aria-label="Date" />
							<Input
								bind:value={revision.author}
								placeholder="Author"
								class="h-9"
								aria-label="Author"
							/>
							<Input
								bind:value={revision.note}
								placeholder="Change"
								class="h-9"
								aria-label="Change"
							/>
							<Button
								variant="ghost"
								size="icon"
								class="size-9 text-muted-foreground hover:text-destructive"
								onclick={() =>
									(branding.revisions = branding.revisions.filter((_, i) => i !== index))}
								aria-label="Remove revision"
							>
								<Trash2Icon class="size-3.5" />
							</Button>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</section>

	<Separator />

	<section class="space-y-4">
		{@render group('Legal')}
		<FormField label="Confidentiality statement">
			{#snippet children({ id })}
				<Textarea {id} bind:value={branding.confidentiality_statement} rows={3} class="text-sm" />
			{/snippet}
		</FormField>
		<FormField label="Disclaimer">
			{#snippet children({ id })}
				<Textarea {id} bind:value={branding.disclaimer} rows={3} class="text-sm" />
			{/snippet}
		</FormField>
	</section>
</div>
