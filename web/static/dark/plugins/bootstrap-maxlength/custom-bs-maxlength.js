$('input.basic').maxlength();
$('input.threshold').maxlength({
    threshold: 20,
});
$('input.few-options').maxlength({
    alwaysShow: true,
    threshold: 10,
    warningClass: "badge badge-secondary",
    limitReachedClass: "badge badge-warning"
});
$('input.alloptions').maxlength({
  	alwaysShow: true,
  	threshold: 10,
  	warningClass: "badge badge-secondary",
    limitReachedClass: "badge badge-dark",
  	separator: ' of ',
  	preText: 'You have ',
  	postText: ' chars remaining.',
  	validate: true
});
$('textarea.textarea').maxlength({
    alwaysShow: true,
});

// Positions
$('input.placement-top-left').maxlength({
    placement:"top-left",
    alwaysShow: true
});
$('input.placement-top').maxlength({
    placement:"top",
    alwaysShow: true
});
$('input.placement-top-right').maxlength({
    placement:"top-right",
    alwaysShow: true
});
$('input.placement-left').maxlength({
    placement:"left",
    alwaysShow: true
});
$('input.placement-right').maxlength({
    placement:"right",
    alwaysShow: true
});
$('input.placement-bottom-left').maxlength({
    placement:"bottom-left",
    alwaysShow: true
});
$('input.placement-bottom').maxlength({
    placement:"bottom",
    alwaysShow: true
});
$('input.placement-bottom-right').maxlength({
    placement:"bottom-right",
    alwaysShow: true
});