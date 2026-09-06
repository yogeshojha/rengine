export const WORDLIST_KINDS = ['subdomain', 'vhost', 'content'] as const;
export type WordlistKind = (typeof WORDLIST_KINDS)[number];

export const WORDLIST_KIND_LABELS: Record<WordlistKind, string> = {
	subdomain: 'Subdomain names',
	vhost: 'Virtual host names',
	content: 'Paths and files'
};

export interface Wordlist {
	id: string;
	slug: string;
	name: string;
	description: string;
	origin: 'builtin' | 'custom';
	kind: WordlistKind;
	words: number;
	bytes: number;
	created_at: string;
	updated_at: string;
}

export interface WordlistFile {
	filename: string;
	content: string;
	name?: string;
	description?: string;
}

export interface WordlistUpload {
	kind: WordlistKind;
	files: WordlistFile[];
}

export interface WordlistRejection {
	filename: string;
	reason: string;
}

export interface WordlistUploadResult {
	stored: Wordlist[];
	rejected: WordlistRejection[];
}
