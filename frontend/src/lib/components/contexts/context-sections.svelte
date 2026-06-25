<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { SvelteSet } from 'svelte/reactivity';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Info from '@lucide/svelte/icons/info';

	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import * as Popover from '$lib/components/ui/popover';

	import AuthSection from './auth-section.svelte';
	import RateSection from './rate-section.svelte';
	import ScopeSection from './scope-section.svelte';
	import RuntimeSection from './runtime-section.svelte';
	import ProxySection from './proxy-section.svelte';
	import { markTouchedSecrets, type ContextFormSection } from './context-form';
	import type { ScanContextCreate, AuthConfig, AuthHeader } from '$lib/types/scan-context';

	const ALL_SECTIONS: ContextFormSection[] = [
		'identity',
		'auth',
		'rate',
		'scope',
		'runtime',
		'proxy'
	];

	interface Props {
		draft: ScanContextCreate;
		open: Record<ContextFormSection, boolean>;
		touched: SvelteSet<string>;
		onPatch: (updates: Partial<ScanContextCreate>) => void;
		sections?: ContextFormSection[];
		seedKey?: number;
	}

	let {
		draft,
		open = $bindable(),
		touched,
		onPatch,
		sections = ALL_SECTIONS,
		seedKey = 0
	}: Props = $props();

	const META: Record<ContextFormSection, { title: string; subtitle: string }> = {
		identity: { title: 'Identity', subtitle: 'Name and description' },
		auth: { title: 'Authentication', subtitle: 'How requests authenticate to the target' },
		rate: { title: 'Rate Limiting', subtitle: 'Throughput ceilings and concurrency' },
		scope: { title: 'Scope', subtitle: 'Include / exclude rules for assets' },
		runtime: { title: 'Runtime Options', subtitle: 'Protocol and redirect behaviour' },
		proxy: { title: 'Proxy', subtitle: 'Route scan traffic through a proxy' }
	};

	function handleAuthChange(next: { auth: AuthConfig; extraHeaders: AuthHeader[] }) {
		markTouchedSecrets(next.auth, touched);
		onPatch({
			auth_type: next.auth.auth_type as ScanContextCreate['auth_type'],
			auth: next.auth,
			extra_headers: next.extraHeaders
		});
	}
</script>

{#snippet section(
	key: ContextFormSection,
	title: string,
	subtitle: string,
	content: Snippet,
	info?: Snippet
)}
	<Card.Root>
		<Collapsible.Root bind:open={open[key]}>
			<Card.Header class="flex flex-row items-center justify-between gap-2 py-4 text-left">
				<Collapsible.Trigger class="flex min-w-0 flex-1 items-center justify-between gap-2">
					<div class="min-w-0">
						<Card.Title class="text-sm">{title}</Card.Title>
						<Card.Description class="text-xs">{subtitle}</Card.Description>
					</div>
					<ChevronDown
						class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {open[key]
							? 'rotate-180'
							: ''}"
					/>
				</Collapsible.Trigger>
				{#if info}
					<Popover.Root>
						<Popover.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="h-7 w-7 shrink-0 text-muted-foreground"
									aria-label="Merge behaviour"
								>
									<Info class="h-3.5 w-3.5" />
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="w-72 text-xs text-muted-foreground">
							{@render info()}
						</Popover.Content>
					</Popover.Root>
				{/if}
			</Card.Header>
			<Collapsible.Content>
				<Card.Content class="pb-5">
					{@render content()}
				</Card.Content>
			</Collapsible.Content>
		</Collapsible.Root>
	</Card.Root>
{/snippet}

{#snippet authInfo()}
	<p class="mb-1 font-medium text-foreground">Merge behaviour</p>
	<ul class="space-y-1 pl-3">
		<li class="list-disc">Headers: engine ∪ context — context wins on conflict.</li>
		<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
	</ul>
{/snippet}

{#snippet rateInfo()}
	<p class="mb-1 font-medium text-foreground">Merge behaviour</p>
	<ul class="space-y-1 pl-3">
		<li class="list-disc">Context rate overrides take precedence over engine defaults.</li>
		<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
	</ul>
{/snippet}

{#snippet identityBody()}
	<div class="space-y-4">
		<div class="space-y-1.5">
			<Label class="text-xs">Name</Label>
			<Input
				value={draft.name}
				placeholder="e.g. Authenticated staging"
				class="h-9"
				oninput={(e) => onPatch({ name: e.currentTarget.value })}
			/>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Description</Label>
			<Textarea
				value={draft.description ?? ''}
				placeholder="What this context is for (optional)"
				class="min-h-20"
				oninput={(e) => onPatch({ description: e.currentTarget.value || null })}
			/>
		</div>
	</div>
{/snippet}

{#snippet authBody()}
	{#key seedKey}
		<AuthSection
			auth={draft.auth as AuthConfig}
			extraHeaders={draft.extra_headers}
			onChange={handleAuthChange}
		/>
	{/key}
{/snippet}

{#snippet rateBody()}
	<RateSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet scopeBody()}
	<ScopeSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet runtimeBody()}
	<RuntimeSection context={draft} onChange={onPatch} />
{/snippet}

{#snippet proxyBody()}
	<ProxySection context={draft} onChange={onPatch} />
{/snippet}

{#snippet sectionFor(key: ContextFormSection)}
	{#if key === 'identity'}
		{@render section('identity', META.identity.title, META.identity.subtitle, identityBody)}
	{:else if key === 'auth'}
		{@render section('auth', META.auth.title, META.auth.subtitle, authBody, authInfo)}
	{:else if key === 'rate'}
		{@render section('rate', META.rate.title, META.rate.subtitle, rateBody, rateInfo)}
	{:else if key === 'scope'}
		{@render section('scope', META.scope.title, META.scope.subtitle, scopeBody)}
	{:else if key === 'runtime'}
		{@render section('runtime', META.runtime.title, META.runtime.subtitle, runtimeBody)}
	{:else if key === 'proxy'}
		{@render section('proxy', META.proxy.title, META.proxy.subtitle, proxyBody)}
	{/if}
{/snippet}

<div class="space-y-4">
	{#each sections as key (key)}
		{@render sectionFor(key)}
	{/each}
</div>
