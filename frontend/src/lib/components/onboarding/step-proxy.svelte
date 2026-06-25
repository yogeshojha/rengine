<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Separator } from '$lib/components/ui/separator';
	import * as Select from '$lib/components/ui/select';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { proxiesApi } from '$lib/api/proxies';
	import { PROXY_SCHEMES, PROXY_SCHEME_LABELS, type ProxyEndpoint } from '$lib/types/proxy';
	import type { StepProps } from '$lib/types/onboarding';
	import type { Component } from 'svelte';
	import { toast } from 'svelte-sonner';
	import RepeatIcon from '@lucide/svelte/icons/repeat';
	import ListIcon from '@lucide/svelte/icons/list';
	import CircleSlashIcon from '@lucide/svelte/icons/circle-slash';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import InfoIcon from '@lucide/svelte/icons/info';

	let { data, next, setFooter }: StepProps = $props();

	type ProxyChoice = 'none' | 'single' | 'list';

	let choice = $state<ProxyChoice>('none');
	let busy = $state(false);

	let single = $state<ProxyEndpoint>({
		scheme: 'http',
		host: '',
		port: 8080,
		username: '',
		password: ''
	});

	let listText = $state('');

	const CHOICES: {
		value: ProxyChoice;
		label: string;
		hint: string;
		icon: Component;
		recommended?: boolean;
	}[] = [
		{
			value: 'none',
			label: 'No proxy',
			hint: 'Send recon traffic directly from this host.',
			icon: CircleSlashIcon
		},
		{
			value: 'single',
			label: 'Single rotating proxy',
			hint: 'One gateway that rotates the exit IP per request.',
			icon: RepeatIcon,
			recommended: true
		},
		{
			value: 'list',
			label: 'Multiple static proxies',
			hint: 'A pool of fixed endpoints you maintain yourself.',
			icon: ListIcon
		}
	];

	const LIST_PLACEHOLDER =
		'http://user:pass@host:8080\nsocks5://10.0.0.4:1080\nhttps://gate.provider.com:3128';

	const PROVIDERS = [
		{
			name: 'Bright Data',
			note: 'Large residential and datacenter pools with per-request rotation.',
			url: 'https://brightdata.com'
		},
		{
			name: 'Smartproxy',
			note: 'Residential and ISP proxies with a simple rotating gateway.',
			url: 'https://smartproxy.com'
		},
		{
			name: 'Oxylabs',
			note: 'Enterprise residential and datacenter proxy infrastructure.',
			url: 'https://oxylabs.io'
		}
	];

	function setSinglePort(raw: string) {
		const n = Math.trunc(Number(raw));
		single.port = Number.isFinite(n) && n > 0 ? n : 0;
	}

	function parseLine(line: string): ProxyEndpoint | null {
		const trimmed = line.trim();
		if (!trimmed) return null;
		const m = trimmed.match(/^(https?|socks5):\/\/(?:([^:@/]+)(?::([^@/]*))?@)?([^:/]+):(\d+)$/i);
		if (!m) return null;
		const [, scheme, user, pass, host, port] = m;
		return {
			scheme: scheme.toLowerCase(),
			host,
			port: Number(port),
			username: user || null,
			password: pass || null
		};
	}

	let parsedList = $derived(
		listText
			.split('\n')
			.map(parseLine)
			.filter((e): e is ProxyEndpoint => e !== null)
	);

	let invalidLines = $derived(
		listText.split('\n').filter((l) => l.trim() !== '' && parseLine(l) === null).length
	);

	function buildEndpoints(): ProxyEndpoint[] | null {
		if (choice === 'single') {
			if (!single.host.trim() || !single.port) return null;
			return [
				{
					scheme: single.scheme,
					host: single.host.trim(),
					port: single.port,
					username: single.username?.trim() || null,
					password: single.password || null
				}
			];
		}
		if (choice === 'list') {
			return parsedList.length > 0 ? parsedList : null;
		}
		return null;
	}

	let configured = $derived(choice !== 'none' && buildEndpoints() !== null);

	let testedId = $state<string | null>(null);

	$effect(() => {
		void buildEndpoints();
		testedId = null;
	});

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	async function persist(asDefault: boolean): Promise<string | null> {
		const endpoints = buildEndpoints();
		if (!endpoints) return null;
		const created = await proxiesApi.create({
			name: `${data.instanceName || 'reNgine'} Proxy`,
			mode: choice === 'single' ? 'rotating' : 'single',
			is_active: true,
			is_default: asDefault,
			endpoints
		});
		return created.id;
	}

	async function handleTest() {
		if (!configured) {
			toast.error('Add a proxy endpoint before testing');
			return;
		}
		busy = true;
		try {
			const id = testedId ?? (await persist(false));
			if (!id) return;
			testedId = id;
			const result = await proxiesApi.test(id);
			if (result.success) {
				const ms = result.latency_ms != null ? ` (${result.latency_ms} ms)` : '';
				toast.success(`Proxy reachable${ms}`);
			} else {
				toast.error(result.message || 'Proxy test failed');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to test proxy');
		} finally {
			busy = false;
		}
	}

	async function handleNext() {
		if (choice === 'none' || !configured) {
			next();
			return;
		}
		busy = true;
		try {
			if (testedId) {
				await proxiesApi.setDefault(testedId);
			} else {
				await persist(true);
			}
			toast.success('Proxy saved as the default');
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save proxy');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<RadioGroup.Root
		value={choice}
		onValueChange={(v) => (choice = v as ProxyChoice)}
		class="grid gap-2.5"
	>
		{#each CHOICES as opt (opt.value)}
			{@const Icon = opt.icon}
			<Label
				class="flex cursor-pointer items-start gap-3 rounded-lg border border-input bg-transparent px-4 py-3.5 transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
				data-active={choice === opt.value}
			>
				<RadioGroup.Item value={opt.value} class="mt-0.5" />
				<Icon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
				<span class="min-w-0 flex-1 space-y-0.5">
					<span class="flex items-center gap-2 text-sm font-medium">
						{opt.label}
						{#if opt.recommended}
							<span
								class="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
							>
								Recommended
							</span>
						{/if}
					</span>
					<span class="block text-xs text-muted-foreground">{opt.hint}</span>
				</span>
			</Label>
		{/each}
	</RadioGroup.Root>

	{#if choice === 'single'}
		<div class="space-y-4 rounded-lg border bg-muted/30 p-4">
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-[7rem_1fr_6rem]">
				<div class="space-y-1.5">
					<Label class="text-xs">Scheme</Label>
					<Select.Root
						type="single"
						value={single.scheme}
						onValueChange={(v) => (single.scheme = v ?? 'http')}
					>
						<Select.Trigger class="h-9 w-full text-sm">
							{PROXY_SCHEME_LABELS[single.scheme as keyof typeof PROXY_SCHEME_LABELS] ?? 'HTTP'}
						</Select.Trigger>
						<Select.Content>
							{#each PROXY_SCHEMES as s (s)}
								<Select.Item value={s} label={PROXY_SCHEME_LABELS[s]}
									>{PROXY_SCHEME_LABELS[s]}</Select.Item
								>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
				<div class="space-y-1.5">
					<Label class="text-xs">Host</Label>
					<Input
						value={single.host}
						placeholder="gate.provider.com"
						class="h-9 font-mono text-xs"
						autocomplete="off"
						oninput={(e) => (single.host = e.currentTarget.value)}
					/>
				</div>
				<div class="space-y-1.5">
					<Label class="text-xs">Port</Label>
					<Input
						type="number"
						min="1"
						max="65535"
						value={single.port || ''}
						placeholder="8080"
						class="h-9 font-mono text-xs"
						oninput={(e) => setSinglePort(e.currentTarget.value)}
					/>
				</div>
			</div>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label class="text-xs"
						>Username <span class="text-muted-foreground">(optional)</span></Label
					>
					<Input
						value={single.username ?? ''}
						placeholder="username"
						class="h-9 font-mono text-xs"
						autocomplete="off"
						oninput={(e) => (single.username = e.currentTarget.value)}
					/>
				</div>
				<div class="space-y-1.5">
					<Label class="text-xs"
						>Password <span class="text-muted-foreground">(optional)</span></Label
					>
					<Input
						type="password"
						value={single.password ?? ''}
						placeholder="password"
						class="h-9 font-mono text-xs"
						autocomplete="off"
						oninput={(e) => (single.password = e.currentTarget.value)}
					/>
				</div>
			</div>
		</div>
	{:else if choice === 'list'}
		<div class="space-y-2.5 rounded-lg border bg-muted/30 p-4">
			<Label class="text-xs">Proxy endpoints — one URL per line</Label>
			<Textarea
				value={listText}
				placeholder={LIST_PLACEHOLDER}
				class="min-h-32 font-mono text-xs"
				spellcheck={false}
				oninput={(e) => (listText = e.currentTarget.value)}
			/>
			<div class="flex items-center gap-3 text-xs">
				{#if parsedList.length > 0}
					<span class="text-muted-foreground">
						{parsedList.length} endpoint{parsedList.length === 1 ? '' : 's'} parsed
					</span>
				{/if}
				{#if invalidLines > 0}
					<span class="text-muted-foreground">
						{invalidLines} line{invalidLines === 1 ? '' : 's'} not recognized
					</span>
				{/if}
				{#if parsedList.length === 0 && invalidLines === 0}
					<span class="text-muted-foreground">Format: scheme://[user:pass@]host:port</span>
				{/if}
			</div>
		</div>
	{/if}

	{#if choice !== 'none'}
		<div>
			<Button
				variant="outline"
				size="sm"
				class="h-8 text-xs"
				disabled={busy || !configured}
				onclick={handleTest}
			>
				{#if busy}
					<Spinner class="mr-1.5 size-4" />
				{:else}
					<FlaskConicalIcon class="mr-1.5 size-4" />
				{/if}
				Test connection
			</Button>
			<p class="mt-1.5 text-[11px] text-muted-foreground">
				Saves the proxy and runs a live reachability check. It becomes the default only when you
				continue.
			</p>
		</div>
	{/if}

	<Separator />

	<div class="space-y-3">
		<div class="flex items-start gap-2">
			<InfoIcon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
			<p class="text-xs text-muted-foreground">
				Need a proxy provider? These are widely used for recon. We have no affiliation and earn
				nothing from these links — bring your own credentials.
			</p>
		</div>
		<div class="grid gap-2.5 sm:grid-cols-3">
			{#each PROVIDERS as p (p.name)}
				<div class="flex flex-col rounded-lg border bg-card p-3.5">
					<span class="text-sm font-medium">{p.name}</span>
					<span class="mt-1 flex-1 text-xs text-muted-foreground">{p.note}</span>
					<a
						href={p.url}
						target="_blank"
						rel="noopener noreferrer"
						class="mt-2.5 inline-flex items-center gap-1 text-xs text-primary hover:underline"
					>
						Learn more <ExternalLinkIcon class="size-4" />
					</a>
				</div>
			{/each}
		</div>
	</div>
</div>
