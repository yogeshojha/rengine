import {
	LayoutDashboard,
	Target,
	History,
	ShieldAlert,
	StickyNote,
	Radar,
	Settings,
	FileText,
	BookOpen,
	Wrench,
	Search,
	Globe,
	ShieldQuestion,
	RadioTower
} from 'lucide-svelte';

export const navMain = [
	{
		title: 'Dashboard',
		url: '/dashboard',
		icon: LayoutDashboard
	},
	{
		title: 'Targets',
		url: '/targets',
		icon: Target
	},
	{
		title: 'Scan History',
		url: '/scans',
		icon: History
	},
	{
		title: 'Vulnerabilities',
		url: '/vulnerabilities',
		icon: ShieldAlert
	},
	{
		title: 'Notes',
		url: '/notes',
		icon: StickyNote
	},
	{
		title: 'Scan Engines',
		url: '/engines',
		icon: Radar,
		items: [
			{
				title: 'Engines',
				url: '/engines'
			},
			{
				title: 'Scan Context',
				url: '/engines/context'
			}
		]
	},
	{
		title: 'Reports',
		url: '/reports',
		icon: FileText
	},
	{
		title: 'Settings',
		url: '/settings',
		icon: Settings
	}
];

export const toolboxItems = [
	{
		title: 'WHOIS Lookup',
		icon: Search,
		action: 'whois'
	},
	{
		title: 'CVE Lookup',
		icon: ShieldQuestion,
		action: 'cve'
	},
	{
		title: 'WAF Detector',
		icon: RadioTower,
		action: 'waf'
	},
	{
		title: 'DNS Lookup',
		icon: Globe,
		action: 'dns'
	}
];

export const quickActions = [
	{
		title: 'Add Target',
		icon: Target,
		action: 'add-target'
	},
	{
		title: 'New Scan',
		icon: Radar,
		action: 'new-scan'
	},
	{
		title: 'Create Engine',
		icon: Wrench,
		action: 'create-engine'
	}
];

export const documentationLink = {
	title: 'Documentation',
	url: 'https://rengine.wiki',
	icon: BookOpen
};