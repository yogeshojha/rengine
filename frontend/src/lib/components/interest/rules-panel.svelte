<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Bell from '@lucide/svelte/icons/bell';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Eye from '@lucide/svelte/icons/eye';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Switch } from '$lib/components/ui/switch';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { interestApi } from '$lib/api/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { kindIcon } from '$lib/config/interest';
	import { RULE_MODE, type InterestRule } from '$lib/types/interest';
	import RuleSheet from './rule-sheet.svelte';

	let rules = $state<InterestRule[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let q = $state('');
	let editing = $state<InterestRule | null>(null);
	let creating = $state(false);
	let removing = $state<InterestRule | null>(null);

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let keywordRule = $derived(rules.find((r) => r.mode === RULE_MODE.KEYWORD && r.builtin) ?? null);
	let queryRules = $derived(
		rules
			.filter((r) => r !== keywordRule)
			.filter((r) => {
				const needle = q.trim().toLowerCase();
				if (!needle) return true;
				return (
					r.name.toLowerCase().includes(needle) ||
					r.query.toLowerCase().includes(needle) ||
					r.kind_label.toLowerCase().includes(needle)
				);
			})
	);

	$effect(() => {
		void interestCatalog.load();
	});

	$effect(() => {
		const id = projectId;
		if (!id) return;
		void load(id);
	});

	async function load(id: string): Promise<void> {
		loading = true;
		try {
			rules = await interestApi.rules(id);
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load the rules';
		} finally {
			loading = false;
		}
	}

	async function patch(rule: InterestRule, body: Record<string, unknown>): Promise<void> {
		try {
			const updated = await interestApi.updateRule(projectId, rule.id, body);
			rules = rules.map((r) => (r.id === updated.id ? updated : r));
		} catch {
			toast.error(`Could not update ${rule.name}`);
		}
	}

	async function remove(): Promise<void> {
		if (!removing) return;
		try {
			await interestApi.deleteRule(projectId, removing.id);
			rules = rules.filter((r) => r.id !== removing!.id);
			toast.success(`${removing.name} deleted`);
		} catch {
			toast.error('Could not delete the rule');
		} finally {
			removing = null;
		}
	}

	function saved(rule: InterestRule): void {
		const exists = rules.some((r) => r.id === rule.id);
		rules = exists ? rules.map((r) => (r.id === rule.id ? rule : r)) : [...rules, rule];
		editing = null;
		creating = false;
	}
</script>

<div class="flex flex-col gap-6">
	{#if keywordRule}
		{@const kr = keywordRule}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<PanelHead title="Keywords" description="Terms that flag a matching asset">
				{#if kr.matches != null}
					<span class="tabular-nums">{kr.matches.toLocaleString()} flagged so far</span>
				{/if}
			</PanelHead>
			<div class="flex flex-col gap-3 px-5 py-4">
				<Input
					value={kr.keywords.join(', ')}
					placeholder="admin, ftp, cpanel, dashboard"
					class="font-mono text-sm"
					onchange={(e) =>
						patch(kr, {
							keywords: e.currentTarget.value
								.split(',')
								.map((w) => w.trim())
								.filter(Boolean)
						})}
				/>
				<div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
					{#each Object.entries(interestCatalog.catalog?.keyword_fields ?? {}) as [key, label] (key)}
						<label class="flex items-center gap-2">
							<Switch
								checked={kr.keyword_fields.includes(key)}
								onCheckedChange={(v) =>
									patch(kr, {
										keyword_fields: v
											? [...kr.keyword_fields, key]
											: kr.keyword_fields.filter((f) => f !== key)
									})}
							/>
							{label}
						</label>
					{/each}
					<label class="flex items-center gap-2">
						<Switch checked={kr.live_only} onCheckedChange={(v) => patch(kr, { live_only: v })} />
						Only assets that answered
					</label>
					<label class="ml-auto flex items-center gap-2">
						<Switch checked={kr.notify} onCheckedChange={(v) => patch(kr, { notify: v })} />
						Notify
					</label>
				</div>
				<p class="text-xs text-muted-foreground">
					Matched against the hostname and the page title. An edit re-labels every past scan.
				</p>
			</div>
		</Card.Root>
	{/if}

	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Rules" description="Saved queries that flag a matching asset">
			<span class="tabular-nums">{queryRules.length} of {rules.length - (keywordRule ? 1 : 0)}</span
			>
		</PanelHead>

		<div class="flex flex-wrap items-center gap-2 border-b px-5 py-2.5">
			<div class="relative min-w-56 flex-1">
				<Search
					class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
				/>
				<Input bind:value={q} placeholder="Filter rules" class="h-8 pl-8 text-sm" />
			</div>
			<Button size="sm" class="h-8" onclick={() => (creating = true)}>
				<Plus class="size-3.5" />
				New rule
			</Button>
		</div>

		{#if loading}
			<div class="flex flex-col gap-2 p-5">
				{#each Array(5) as _, i (i)}
					<Skeleton class="h-10 w-full" />
				{/each}
			</div>
		{:else if error}
			<EmptyState icon={Eye} title="Could not load the rules" description={error} class="py-12" />
		{:else if !queryRules.length}
			<EmptyState
				icon={Eye}
				title={q ? 'No rule matches' : 'No rules yet'}
				description={q ? 'Try a different filter.' : 'Add a rule to start flagging assets.'}
				class="py-12"
			/>
		{:else}
			<div class="divide-y">
				{#each queryRules as rule (rule.id)}
					{@const Icon = kindIcon(rule.kind)}
					<div class="group flex items-center gap-3 px-5 py-3 hover:bg-accent/40">
						<Icon class="size-4 shrink-0 text-muted-foreground" />
						<div class="flex min-w-0 flex-1 flex-col gap-0.5">
							<span class="flex flex-wrap items-center gap-2 text-[12.5px] font-medium">
								{rule.name}
								<span
									class="rounded border border-border px-1 py-px text-[10px] font-normal tracking-[0.04em] text-muted-foreground uppercase"
									>{rule.builtin ? 'Shipped' : 'Custom'}</span
								>
								<span class="text-[11px] font-normal text-muted-foreground">{rule.kind_label}</span>
								{#if rule.notify}
									<Hint text="Notifies when this rule flags a new asset">
										{#snippet child(props)}
											<span {...props}><Bell class="size-3 text-primary" /></span>
										{/snippet}
									</Hint>
								{/if}
							</span>
							<span class="truncate font-mono text-[11px] text-muted-foreground">{rule.query}</span>
						</div>
						<span
							class="w-16 shrink-0 text-right text-[12.5px] tabular-nums {rule.matches
								? ''
								: 'text-muted-foreground'}">{(rule.matches ?? 0).toLocaleString()}</span
						>
						<span class="flex shrink-0 items-center gap-1">
							<Button
								variant="ghost"
								size="icon"
								class="size-7 opacity-0 group-hover:opacity-100"
								onclick={() => (editing = rule)}
								aria-label="Edit {rule.name}"
							>
								<Pencil class="size-3.5" />
							</Button>
							{#if !rule.builtin}
								<Button
									variant="ghost"
									size="icon"
									class="size-7 opacity-0 group-hover:opacity-100"
									onclick={() => (removing = rule)}
									aria-label="Delete {rule.name}"
								>
									<Trash2 class="size-3.5" />
								</Button>
							{/if}
							<Switch
								checked={rule.enabled}
								onCheckedChange={(v) => patch(rule, { enabled: v })}
								aria-label="Enable {rule.name}"
							/>
						</span>
					</div>
				{/each}
			</div>
		{/if}
	</Card.Root>
</div>

<RuleSheet
	rule={editing}
	open={editing !== null || creating}
	{projectId}
	onOpenChange={(v) => {
		if (!v) {
			editing = null;
			creating = false;
		}
	}}
	onSaved={saved}
/>

<DeleteConfirmationDialog
	open={removing !== null}
	onOpenChange={(v) => {
		if (!v) removing = null;
	}}
	title="Delete {removing?.name ?? 'this rule'}?"
	description="The rule is removed and assets it flagged are no longer labelled by it. This action cannot be undone."
	onConfirm={remove}
/>
