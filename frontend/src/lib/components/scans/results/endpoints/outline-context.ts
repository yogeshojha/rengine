import type { TableColumn } from '../table/columns';
import type { EndpointFilter, EndpointRead, MergedLeaf, TreeNode } from '$lib/utilities/endpoints';

export const GUIDE_WIDTH = 'w-5';
export const OUTLINE_ROW_ATTR = 'data-outline-row';
export const LEAF_PAGE = 25;
// a search opens branches only while the result still fits on one screen
export const AUTO_OPEN_ROWS = 40;

export interface Crumb {
	key: string;
	name: string;
}

export const CRUMB_HEIGHT = 32;

export interface OpenBudget {
	enabled: boolean;
	used: number;
	decided: Set<string>;
}

export interface OutlineContext {
	projectId: string;
	scanId: string;
	merged: boolean;
	searching: boolean;
	filter: EndpointFilter;
	columns: TableColumn[];
	terms: string[];
	pad: string;
	expanded: Set<string>;
	budget: OpenBudget;
	focusedKey: string;
	selectedId: string | null;
	toggle: (key: string) => void;
	openEndpoint: (e: EndpointRead) => void;
	openById: (id: string) => void;
	openMerged: (leaf: MergedLeaf) => void;
	onFilter: (token: string) => void;
	onShowInList: (token: string) => void;
	onHost: (host: string) => void;
	copyBranch: (node: TreeNode) => void;
	copyWordlist: (node: TreeNode) => void;
	verifyBranch?: (node: TreeNode) => void;
}

export function nodeCost(node: TreeNode, children: TreeNode[]): number {
	const kids = node.lazy && !children.length ? node.folders : children.length;
	return kids + Math.min(node.direct_count, LEAF_PAGE);
}
