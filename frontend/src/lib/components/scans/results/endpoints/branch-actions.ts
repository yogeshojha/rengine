import { toast } from 'svelte-sonner';
import { endpointsApi } from '$lib/api/scan-results';
import { writeClipboard } from '$lib/utilities/clipboard';
import type { EndpointFilter, TreeNode } from '$lib/utilities/endpoints';

export const COPY_CAP = 5000;
const COPY_PAGE = 200;

export interface BranchScope {
	projectId: string;
	scanId: string;
	filter: EndpointFilter;
	merged?: boolean;
}

export function branchFilter(scope: BranchScope, node: TreeNode): EndpointFilter {
	return {
		...scope.filter,
		host: scope.merged ? null : node.host,
		dir_path: node.kind === 'host' ? null : node.path,
		subtree: true,
		sort: 'path',
		direction: 'asc',
		size: COPY_PAGE,
		page: 1
	};
}

export async function collectUrls(
	scope: BranchScope,
	node: TreeNode
): Promise<{ urls: string[]; capped: boolean }> {
	const base = branchFilter(scope, node);
	const urls: string[] = [];
	for (let page = 1; urls.length < COPY_CAP; page++) {
		const res = await endpointsApi.search(scope.projectId, scope.scanId, { ...base, page });
		urls.push(...res.items.map((e) => e.url));
		if (res.items.length < COPY_PAGE || urls.length >= res.total) break;
	}
	return { urls: [...new Set(urls)].slice(0, COPY_CAP), capped: urls.length >= COPY_CAP };
}

export async function copyBranch(scope: BranchScope, node: TreeNode) {
	try {
		const { urls, capped } = await collectUrls(scope, node);
		await writeClipboard(urls.join('\n'));
		toast.success(
			`Copied ${urls.length.toLocaleString()} ${urls.length === 1 ? 'URL' : 'URLs'}${
				capped ? ' (first 5,000)' : ''
			}`
		);
	} catch {
		toast.error('The URLs could not be copied.');
	}
}

export async function copyWordlist(scope: BranchScope, node: TreeNode) {
	try {
		const { urls, capped } = await collectUrls(scope, node);
		const prefix = node.kind === 'host' || node.kind === 'group' ? '/' : node.path;
		const words = new Set<string>();
		for (const raw of urls) {
			try {
				const path = new URL(raw).pathname;
				const rel = path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\//, '');
				if (rel) words.add(rel);
			} catch {
				// an unparsable url has no path to offer
			}
		}
		await writeClipboard([...words].sort().join('\n'));
		toast.success(
			`Copied ${words.size.toLocaleString()} ${words.size === 1 ? 'path' : 'paths'}${capped ? ' (first 5,000 URLs)' : ''}`
		);
	} catch {
		toast.error('The paths could not be copied.');
	}
}

export function hostNode(host: string): TreeNode {
	return {
		key: `${host}/`,
		name: host,
		path: '/',
		host,
		kind: 'host',
		depth: 0,
		direct_count: 0,
		subtree_count: 0,
		child_count: 0,
		hosts: 1,
		status_mix: {},
		class_mix: {},
		sources: [],
		interest: [],
		has_params: false,
		params: 0,
		verified: 0,
		unprobed: 0,
		new_count: 0,
		gone_count: 0,
		anomaly: null,
		archive_only: false,
		glyph: 'folder',
		sample_url: null,
		leaf: null,
		query: `host:${host}`,
		children: [],
		lazy: false,
		folders: 0,
		top_folders: [],
		chips: [],
		api: 0,
		walled: 0,
		unfiltered_count: 0,
		identity: null
	};
}
