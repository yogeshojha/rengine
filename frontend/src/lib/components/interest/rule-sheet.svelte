<script lang="ts">
	import { toast } from 'svelte-sonner';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Select from '$lib/components/ui/select';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Switch } from '$lib/components/ui/switch';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { interestApi } from '$lib/api/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { RULE_MODE, type InterestRule, type RulePreview } from '$lib/types/interest';

	interface Props {
		rule: InterestRule | null;
		open: boolean;
		projectId: string;
		onOpenChange: (open: boolean) => void;
		onSaved: (rule: InterestRule) => void;
	}

	let { rule, open, projectId, onOpenChange, onSaved }: Props = $props();

	let name = $state('');
	let description = $state('');
	let query = $state('');
	let kind = $state('other');
	let notify = $state(false);
	let enabled = $state(true);
	let saving = $state(false);
	let preview = $state<RulePreview | null>(null);
	let checking = $state(false);

	let isEdit = $derived(rule !== null);
	let locked = $derived(rule?.builtin === true);
	let kinds = $derived(interestCatalog.catalog?.kinds ?? []);
	let kindLabel = $derived(kinds.find((k) => k.key === kind)?.label ?? 'Pick a reason');

	$effect(() => {
		if (!open) return;
		name = rule?.name ?? '';
		description = rule?.description ?? '';
		query = rule?.query ?? '';
		kind = rule?.kind ?? 'other';
		notify = rule?.notify ?? false;
		enabled = rule?.enabled ?? true;
		preview = null;
	});

	async function check(): Promise<void> {
		if (!query.trim()) return;
		checking = true;
		try {
			preview = await interestApi.preview(query);
		} catch {
			preview = null;
		} finally {
			checking = false;
		}
	}

	async function save(): Promise<void> {
		if (!name.trim()) {
			toast.error('Give the rule a name.');
			return;
		}
		if (!locked && !query.trim()) {
			toast.error('Add a query.');
			return;
		}
		saving = true;
		try {
			const body = {
				name: name.trim(),
				description: description.trim() || null,
				mode: RULE_MODE.QUERY,
				query: query.trim(),
				kind,
				notify,
				enabled
			};
			const saved = isEdit
				? await interestApi.updateRule(projectId, rule!.id, body)
				: await interestApi.createRule(projectId, body);
			toast.success(isEdit ? `${saved.name} saved` : `${saved.name} added`);
			onSaved(saved);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not save the rule');
		} finally {
			saving = false;
		}
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>{isEdit ? rule?.name : 'New rule'}</Sheet.Title>
			<Sheet.Description>
				{locked
					? 'A shipped rule keeps its query. You can change whether it runs and whether it notifies.'
					: 'A rule is a saved query. Anything it matches is flagged as worth a look.'}
			</Sheet.Description>
		</Sheet.Header>

		<ScrollArea.Root class="min-h-0 flex-1">
			<div class="flex flex-col gap-4 px-5 py-4">
				<FormField label="Name">
					{#snippet children(props)}
						<Input {...props} bind:value={name} disabled={locked} placeholder="Admin interfaces" />
					{/snippet}
				</FormField>

				<FormField label="Reason" description="Reason recorded on a flagged asset">
					{#snippet children(props)}
						<Select.Root type="single" bind:value={kind} disabled={locked}>
							<Select.Trigger {...props}>{kindLabel}</Select.Trigger>
							<Select.Content>
								{#each kinds as k (k.key)}
									<Select.Item value={k.key} label={k.label}>{k.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					{/snippet}
				</FormField>

				<FormField label="Query" description="The Web Assets search language">
					{#snippet children(props)}
						<Textarea
							{...props}
							bind:value={query}
							disabled={locked}
							rows={3}
							class="font-mono text-sm"
							placeholder="host:admin and is:live and not is:auth"
							onblur={check}
						/>
					{/snippet}
				</FormField>

				{#if preview?.error}
					<p class="text-xs text-destructive">{preview.error}</p>
				{:else if checking}
					<p class="text-xs text-muted-foreground">Checking…</p>
				{:else if preview}
					<p class="text-xs text-muted-foreground">The query is valid.</p>
				{/if}

				<FormField label="Description" description="Shown as the reason on a flagged asset">
					{#snippet children(props)}
						<Textarea {...props} bind:value={description} disabled={locked} rows={2} />
					{/snippet}
				</FormField>

				<label class="flex items-center justify-between gap-4 text-sm">
					<span class="flex flex-col gap-0.5">
						Notify me
						<span class="text-xs text-muted-foreground">
							Sends a notification the first time this rule flags an asset.
						</span>
					</span>
					<Switch bind:checked={notify} />
				</label>

				<label class="flex items-center justify-between gap-4 text-sm">
					<span>Enabled</span>
					<Switch bind:checked={enabled} />
				</label>
			</div>
		</ScrollArea.Root>

		<Sheet.Footer class="flex-row justify-end gap-2 border-t px-5 py-3">
			<Button variant="outline" size="sm" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton size="sm" loading={saving} loadingLabel="Saving" onclick={save}>
				{isEdit ? 'Save' : 'Add rule'}
			</LoadingButton>
		</Sheet.Footer>
	</Sheet.Content>
</Sheet.Root>
