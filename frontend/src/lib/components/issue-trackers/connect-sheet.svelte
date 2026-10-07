<script lang="ts">
	import { untrack } from 'svelte';
	import CheckIcon from '@lucide/svelte/icons/check';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import DestinationPicker from './destination-picker.svelte';
	import { toast } from 'svelte-sonner';
	import { pluralLabel } from '$lib/utilities/strings';
	import { issueTrackersApi } from '$lib/api/issue-trackers';
	import { issueTrackers } from '$lib/stores/issue-trackers.svelte';
	import { MASK } from '$lib/constants';
	import { TRACKERS, TRACKERS_BY_KIND, TrackerKind } from '$lib/config/issue-trackers';
	import type { IssueTracker, TestResult } from '$lib/types/issue-tracker';

	interface Props {
		open: boolean;
		editing: IssueTracker | null;
	}

	let { open = $bindable(), editing }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-wide text-muted-foreground uppercase';

	let kind = $state<string>(TrackerKind.JIRA_CLOUD);
	let name = $state('');
	let url = $state('');
	let config = $state<Record<string, string>>({});
	let destination = $state('');
	let issueType = $state('');
	let saving = $state(false);
	let testing = $state(false);
	let result = $state<TestResult | null>(null);
	let initial = $state('');

	const spec = $derived(TRACKERS_BY_KIND[kind]);
	const stored = $derived(editing?.config_masked ?? {});
	const missing = $derived(
		!name.trim() ||
			(!url.trim() && !spec.defaultUrl) ||
			spec.fields.some((f) => !config[f.key]?.trim() && !(editing && stored[f.key]))
	);
	const dirty = $derived(
		snapshot() !== initial || Object.values(config).some((value) => value.trim() !== '')
	);
	const guard = new DiscardGuard(
		() => dirty,
		() => (open = false)
	);

	function snapshot(): string {
		return JSON.stringify([kind, name.trim(), url.trim(), destination.trim(), issueType.trim()]);
	}

	$effect(() => {
		if (!open) return;
		result = null;
		if (editing) {
			kind = editing.kind;
			name = editing.name;
			url = editing.url;
			config = {};
			destination = editing.destination ?? '';
			issueType = editing.issue_type ?? '';
		} else {
			kind = TrackerKind.JIRA_CLOUD;
			name = TRACKERS_BY_KIND[TrackerKind.JIRA_CLOUD].label;
			url = '';
			config = {};
			destination = '';
			issueType = '';
		}
		initial = untrack(snapshot);
	});

	function pickKind(next: string) {
		kind = next;
		config = {};
		result = null;
		url = '';
		if (!name.trim() || TRACKERS.some((t) => t.label === name)) name = TRACKERS_BY_KIND[next].label;
	}

	function configBody(): Record<string, string> {
		const out: Record<string, string> = {};
		for (const f of spec.fields) {
			const typed = config[f.key]?.trim();
			if (typed) out[f.key] = typed;
			else if (editing && stored[f.key]) out[f.key] = stored[f.key];
		}
		return out;
	}

	async function test() {
		testing = true;
		result = null;
		try {
			result = await issueTrackersApi.testConfig({
				kind,
				url: url.trim() || null,
				config: configBody(),
				tracker_id: editing?.id ?? null
			});
		} catch (e) {
			result = {
				success: false,
				message: e instanceof Error ? e.message : 'Connection not tested'
			};
		} finally {
			testing = false;
		}
	}

	async function save() {
		saving = true;
		try {
			const body = {
				name: name.trim(),
				url: url.trim() || null,
				destination: destination.trim() || null,
				issue_type: spec.hasIssueType ? issueType.trim() || null : null
			};
			const typedConfig = spec.fields.some((f) => config[f.key]?.trim());
			const row = editing
				? await issueTrackersApi.update(editing.id, {
						...body,
						...(typedConfig ? { config: configBody() } : {})
					})
				: await issueTrackersApi.create({ ...body, kind, config: configBody() });
			issueTrackers.upsert(row);
			toast.success(editing ? `${row.name} saved` : `${row.name} connected`);
			open = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tracker not saved');
		} finally {
			saving = false;
		}
	}
</script>

<Sheet.Root bind:open={() => open, (next) => (next ? (open = true) : !saving && guard.close())}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>{editing ? editing.name : 'Connect a tracker'}</Sheet.Title>
			<Sheet.Description class="sr-only">
				Tracker connection and the default destination for filed issues.
			</Sheet.Description>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col divide-y px-5">
				{#if !editing}
					<section class="flex flex-col gap-2.5 py-5">
						<h3 class={LABEL}>Tracker</h3>
						<ToggleGroup.Root
							type="single"
							variant="outline"
							spacing={1}
							value={kind}
							onValueChange={(v) => v && pickKind(v)}
							class="grid w-full grid-cols-2 gap-1.5"
							aria-label="Tracker"
						>
							{#each TRACKERS as option (option.kind)}
								<ToggleGroup.Item value={option.kind} class="h-9 w-full">
									{option.label}
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</section>
				{/if}

				<section class="flex flex-col gap-4 py-5">
					<h3 class={LABEL}>Connection</h3>
					<FormField label="Name" required>
						{#snippet children({ id })}
							<Input {id} bind:value={name} maxlength={120} placeholder={spec.label} />
						{/snippet}
					</FormField>
					<FormField label={spec.urlLabel} required={!spec.defaultUrl}>
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={url}
								placeholder={spec.urlPlaceholder}
								autocomplete="off"
								spellcheck={false}
							/>
						{/snippet}
					</FormField>
					{#each spec.fields as field (field.key)}
						<FormField
							label={field.label}
							description={field.help || undefined}
							required={!(editing && stored[field.key])}
						>
							{#snippet children({ id })}
								<Input
									{id}
									type={field.secret ? 'password' : 'text'}
									autocomplete={field.secret ? 'new-password' : 'off'}
									spellcheck={false}
									value={config[field.key] ?? ''}
									oninput={(e) => (config[field.key] = e.currentTarget.value)}
									placeholder={editing && stored[field.key]
										? field.secret
											? `Stored ${stored[field.key].replace(MASK, '•••')}`
											: stored[field.key]
										: field.placeholder}
								/>
							{/snippet}
						</FormField>
					{/each}
					{#if result}
						<p
							class="flex min-w-0 items-start gap-1.5 text-sm {result.success
								? 'text-success'
								: 'text-destructive'}"
							role="status"
						>
							{#if result.success}
								<CheckIcon class="mt-0.5 size-4 shrink-0" />
							{:else}
								<XIcon class="mt-0.5 size-4 shrink-0" />
							{/if}
							<span class="wrap-anywhere">{result.message}</span>
						</p>
					{/if}
				</section>

				<section class="flex flex-col gap-4 py-5">
					<h3 class={LABEL}>Default destination</h3>
					<FormField label={spec.destinationLabel}>
						{#snippet children({ id })}
							<DestinationPicker
								{id}
								trackerId={editing?.id ?? null}
								bind:value={destination}
								placeholder={spec.destinationPlaceholder}
								searchLabel={`Search ${pluralLabel(spec.destinationLabel).toLowerCase()}`}
								clearable
							/>
						{/snippet}
					</FormField>
					{#if spec.hasIssueType}
						<FormField label="Issue type" description="Default: Bug, then Task.">
							{#snippet children({ id })}
								<DestinationPicker
									{id}
									kind="issue-type"
									trackerId={editing?.id ?? null}
									{destination}
									bind:value={issueType}
									placeholder="Bug"
									clearable
								/>
							{/snippet}
						</FormField>
					{/if}
				</section>
			</div>
		</ScrollArea>

		<Sheet.Footer class="flex-row items-center justify-between gap-2 border-t px-5 py-3">
			<LoadingButton
				variant="ghost"
				size="sm"
				loading={testing}
				loadingLabel="Testing"
				disabled={missing || saving}
				onclick={test}
			>
				Test connection
			</LoadingButton>
			<div class="flex items-center gap-2">
				<Button variant="outline" size="sm" disabled={saving} onclick={() => guard.close()}>
					Cancel
				</Button>
				<LoadingButton
					size="sm"
					loading={saving}
					loadingLabel={editing ? 'Saving' : 'Connecting'}
					disabled={missing}
					onclick={save}
				>
					{editing ? 'Save' : 'Connect'}
				</LoadingButton>
			</div>
		</Sheet.Footer>
	</Sheet.Content>
</Sheet.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
