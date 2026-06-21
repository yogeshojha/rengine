const scope = $state({
	targetId: undefined as string | undefined,
	scanId: undefined as string | undefined
});

export const activityScope = {
	get targetId() {
		return scope.targetId;
	},
	set targetId(v: string | undefined) {
		scope.targetId = v;
	},

	get scanId() {
		return scope.scanId;
	},
	set scanId(v: string | undefined) {
		scope.scanId = v;
	},

	get hasTarget() {
		return !!scope.targetId;
	},
	get hasScan() {
		return !!scope.scanId;
	},

	clear() {
		scope.targetId = undefined;
		scope.scanId = undefined;
	}
};
