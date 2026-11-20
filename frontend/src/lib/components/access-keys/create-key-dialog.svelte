<script lang="ts">
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import CodeBlock from '$lib/components/code-block.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { accessKeysApi } from '$lib/api/access-keys';
	import {
		ACCESS_KEY_LEVELS,
		AccessKeyLevel,
		DEFAULT_EXPIRY_DAYS,
		EXPIRY_DAYS,
		EXPIRY_LABELS,
		LEVEL_HELP,
		LEVEL_LABELS,
		MAX_NAME_LENGTH,
		expiryDays,
		expiryValue
	} from '$lib/config/access-keys';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { requestFor } from '$lib/utilities/access-keys';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import type { AccessKey, AccessKeyCreated } from '$lib/types/access-key';

	interface Props {
		open: boolean;
		oncreated: (key: AccessKey) => void;
	}

	let { open = $bindable(), oncreated }: Props = $props();

	const DEFAULT_EXPIRY = expiryValue(DEFAULT_EXPIRY_DAYS);

	let name = $state('');
	let access = $state<string>(AccessKeyLevel.READ);
	let expiry = $state(DEFAULT_EXPIRY);
	let saving = $state(false);
	let created = $state<AccessKeyCreated | null>(null);
	let copied = $state(false);

	const request = $derived(
		created && typeof window !== 'undefined'
			? requestFor(created.first_request, window.location.origin, projectsStore.activeProject?.id)
			: ''
	);
	const dirty = $derived(
		!created && (!!name.trim() || access !== AccessKeyLevel.READ || expiry !== DEFAULT_EXPIRY)
	);
	const guard = new DiscardGuard(() => dirty, close);

	function reset() {
		name = '';
		access = AccessKeyLevel.READ;
		expiry = DEFAULT_EXPIRY;
		created = null;
		copied = false;
	}

	async function copyKey() {
		if (!created) return;
		if (await writeClipboard(created.key)) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} else {
			toast.error('Access key not copied');
		}
	}

	function close() {
		open = false;
		reset();
	}

	async function submit() {
		if (!name.trim() || saving) return;
		saving = true;
		try {
			created = await accessKeysApi.create({
				name: name.trim(),
				access: access as AccessKeyLevel,
				expires_in_days: expiryDays(expiry)
			});
			const { key: _secret, ...row } = created;
			oncreated(row);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Access key not created');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : !saving && guard.close())}>
	<Dialog.Content class="grid-cols-[minmax(0,1fr)] gap-0 p-0 sm:max-w-lg">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{created ? 'Access key created' : 'New access key'}</Dialog.Title>
			{#if created}
				<Dialog.Description>Shown once. Only a hash is stored.</Dialog.Description>
			{/if}
		</Dialog.Header>

		{#if created}
			<div class="flex min-w-0 flex-col gap-4 px-6 py-5">
				<CodeBlock code={created.key} label={created.name} numbers={false} wrap />
				<CodeBlock code={request} lang="shell" label="Web assets that answer 200" numbers={false} />
			</div>
			<Dialog.Footer class="border-t px-6 py-4">
				<Button variant="outline" onclick={copyKey}>{copied ? 'Copied' : 'Copy key'}</Button>
				<Button onclick={close}>Done</Button>
			</Dialog.Footer>
		{:else}
			<form
				class="flex min-w-0 flex-col"
				onsubmit={(e) => {
					e.preventDefault();
					void submit();
				}}
			>
				<div class="flex flex-col gap-5 px-6 py-5">
					<FormField label="Name" required>
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={name}
								autocomplete="off"
								maxlength={MAX_NAME_LENGTH}
								disabled={saving}
							/>
						{/snippet}
					</FormField>

					<div class="flex flex-col gap-2">
						<span class="text-sm font-medium">Access</span>
						<RadioGroup.Root
							bind:value={access}
							aria-label="Access"
							class="grid gap-2"
							disabled={saving}
						>
							{#each ACCESS_KEY_LEVELS as level (level)}
								<Label
									class="flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 font-normal data-[active=true]:border-primary data-[active=true]:bg-muted"
									data-active={access === level}
								>
									<span class="flex h-5 items-center">
										<RadioGroup.Item value={level} />
									</span>
									<span class="flex flex-col gap-0.5">
										<span class="text-sm leading-5 font-medium">{LEVEL_LABELS[level]}</span>
										<span class="text-xs text-muted-foreground">{LEVEL_HELP[level]}</span>
									</span>
								</Label>
							{/each}
						</RadioGroup.Root>
					</div>

					<div class="flex flex-col gap-2">
						<span class="text-sm font-medium">Expires</span>
						<ToggleGroup.Root
							type="single"
							variant="outline"
							size="sm"
							class="w-full"
							aria-label="Expires"
							value={expiry}
							onValueChange={(v) => v && (expiry = v)}
							disabled={saving}
						>
							{#each EXPIRY_DAYS as days (expiryValue(days))}
								<ToggleGroup.Item value={expiryValue(days)} class="flex-1 text-xs">
									{EXPIRY_LABELS.get(days)}
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</div>
				</div>
				<Dialog.Footer class="border-t px-6 py-4">
					<Button type="button" variant="outline" disabled={saving} onclick={() => guard.close()}>
						Cancel
					</Button>
					<LoadingButton
						type="submit"
						loading={saving}
						loadingLabel="Creating"
						disabled={!name.trim()}
					>
						Create key
					</LoadingButton>
				</Dialog.Footer>
			</form>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
