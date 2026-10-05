export interface CheckLibrary {
	version: string | null;
	checks: number | null;
	synced_at: string | null;
}

export interface ToolVersion {
	name: string;
	version: string;
	url: string;
}

export interface About {
	version: string;
	release_url: string | null;
	mode: string;
	architecture: string | null;
	postgres: string | null;
	redis: string | null;
	check_library: CheckLibrary | null;
	tools: ToolVersion[];
	documentation_url: string;
	issue_url: string;
}
