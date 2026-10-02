const scope = $state({
	targetId: undefined as string | undefined
});

export const activityScope = {
	get targetId() {
		return scope.targetId;
	},
	set targetId(v: string | undefined) {
		scope.targetId = v;
	},

	clear() {
		scope.targetId = undefined;
	}
};
