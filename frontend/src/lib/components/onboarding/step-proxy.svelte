<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Textarea } from '$lib/components/ui/textarea';
	import * as Select from '$lib/components/ui/select';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { proxiesApi } from '$lib/api/proxies';
	import { PROXY_SCHEMES, PROXY_SCHEME_LABELS, type ProxyEndpoint } from '$lib/types/proxy';
	import type { StepProps } from '$lib/types/onboarding';
	import type { IconComponent } from '$lib/config/icons';
	import { PRODUCT_NAME } from '$lib/constants';
	import { plural } from '$lib/utilities/strings';
	import { toast } from 'svelte-sonner';
	import RepeatIcon from '@lucide/svelte/icons/repeat';
	import ListIcon from '@lucide/svelte/icons/list';
	import CircleSlashIcon from '@lucide/svelte/icons/circle-slash';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';

	let { data, next, setFooter }: StepProps = $props();

	type ProxyChoice = 'none' | 'single' | 'list';

	let choice = $state<ProxyChoice>('none');
	let busy = $state(false);
	let testing = $state(false);

	let single = $state<ProxyEndpoint>({
		scheme: PROXY_SCHEMES[0],
		host: '',
		port: 8080,
		username: '',
		password: ''
	});

	let listText = $state('');

	const CHOICES: {
		value: ProxyChoice;
		label: string;
		hint?: string;
		icon: IconComponent;
	}[] = [
		{
			value: 'none',
			label: 'No proxy',
			hint: 'Scan traffic is sent directly from this instance.',
			icon: CircleSlashIcon
		},
		{
			value: 'single',
			label: 'Single proxy',
			icon: RepeatIcon
		},
		{
			value: 'list',
			label: 'Proxy pool',
			hint: 'Each scan uses one endpoint from the pool.',
			icon: ListIcon
		}
	];

	const LIST_PLACEHOLDER =
		'http://user:pass@host:8080\nsocks5://10.0.0.4:1080\nhttps://gate.provider.com:3128';

	const PROXY_URL = new RegExp(
		`^(${PROXY_SCHEMES.join('|')}):\\/\\/(?:([^:@/]+)(?::([^@/]*))?@)?([^:/]+):(\\d+)$`,
		'i'
	);

	function setSinglePort(raw: string) {
		const n = Math.trunc(Number(raw));
		single.port = Number.isFinite(n) && n > 0 ? n : 0;
	}

	function parseLine(line: string): ProxyEndpoint | null {
		const trimmed = line.trim();
		if (!trimmed) return null;
		const m = trimmed.match(PROXY_URL);
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

	let savedId = $state<string | null>(null);
	let saved = $state(false);

	$effect(() => {
		void buildEndpoints();
		saved = false;
	});

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Continue',
			nextLoading: busy,
			nextDisabled: testing,
			canSkip: true
		});
	});

	async function persist(endpoints: ProxyEndpoint[], asDefault: boolean): Promise<string> {
		if (!savedId) {
			const created = await proxiesApi.create({
				name: `${data.instanceName || PRODUCT_NAME} Proxy`,
				is_active: true,
				is_default: asDefault,
				endpoints
			});
			savedId = created.id;
		} else {
			if (!saved) await proxiesApi.update(savedId, { endpoints });
			if (asDefault) await proxiesApi.setDefault(savedId);
		}
		saved = true;
		return savedId;
	}

	async function handleTest() {
		const endpoints = choice === 'none' ? null : buildEndpoints();
		if (!endpoints) {
			toast.error('Enter a proxy endpoint');
			return;
		}
		testing = true;
		try {
			const result = await proxiesApi.test(await persist(endpoints, false));
			if (result.success) {
				const ms = result.latency_ms != null ? ` in ${result.latency_ms} ms` : '';
				toast.success(`Proxy reachable${ms}`);
			} else {
				toast.error(result.message || 'Proxy test failed');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Proxy test failed');
		} finally {
			testing = false;
		}
	}

	async function handleNext() {
		const endpoints = choice === 'none' ? null : buildEndpoints();
		busy = true;
		try {
			if (endpoints) {
				await persist(endpoints, true);
				toast.success('Proxy saved as default');
			} else if (savedId) {
				await proxiesApi.remove(savedId);
				savedId = null;
			}
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Proxy not saved');
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
					<span class="block text-sm font-medium">{opt.label}</span>
					{#if opt.hint}
						<span class="block text-xs text-muted-foreground">{opt.hint}</span>
					{/if}
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
						onValueChange={(v) => (single.scheme = v || PROXY_SCHEMES[0])}
					>
						<Select.Trigger class="h-9 w-full text-sm">
							{PROXY_SCHEME_LABELS[single.scheme as keyof typeof PROXY_SCHEME_LABELS]}
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
					<Label class="text-xs">Username <span class="text-muted-foreground">Optional</span></Label
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
					<Label class="text-xs">Password <span class="text-muted-foreground">Optional</span></Label
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
			<Label class="text-xs">Proxy endpoints, one URL per line</Label>
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
						{plural(parsedList.length, 'endpoint')} parsed
					</span>
				{/if}
				{#if invalidLines > 0}
					<span class="text-muted-foreground">
						{plural(invalidLines, 'line')} not recognized
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
			<LoadingButton
				variant="outline"
				size="sm"
				class="h-8 text-xs"
				loading={testing}
				loadingLabel="Testing"
				disabled={busy || !configured}
				onclick={handleTest}
			>
				<FlaskConicalIcon class="mr-1.5 size-4" />
				Test connection
			</LoadingButton>
			<p class="mt-1.5 text-2xs text-muted-foreground">Saves the proxy and checks reachability.</p>
		</div>
	{/if}
</div>
