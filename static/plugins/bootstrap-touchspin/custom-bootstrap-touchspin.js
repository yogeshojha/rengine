// Example with postfix (large)
$("input[name='demo1']").TouchSpin({
    min: 0,
    max: 100,
    step: 0.1,
    decimals: 2,
    boostat: 5,
    maxboostedstep: 10,
    postfix: '%',
    buttondown_class: "btn btn-classic btn-primary",
    buttonup_class: "btn btn-classic btn-primary"
});

// With prefix
$("input[name='demo2']").TouchSpin({
    min: 0,
    max: 100,
    step: 0.1,
    decimals: 2,
    boostat: 5,
    maxboostedstep: 10,
    prefix: '%',
    buttondown_class: "btn btn-classic btn-primary",
    buttonup_class: "btn btn-classic btn-primary"
});


// Multiple select boxes
$("input[name='demo_vertical']").TouchSpin({
    verticalbuttons: true,
    buttondown_class: "btn btn-classic btn-outline-info",
    buttonup_class: "btn btn-classic btn-outline-danger"
});


// Vertical buttons with custom icons
$("input[name='demo_vertical2']").TouchSpin({
    verticalbuttons: true,
    verticalup: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-up"><polyline points="18 15 12 9 6 15"></polyline></svg>',
    verticaldown: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-down"><polyline points="6 9 12 15 18 9"></polyline></svg>',
    buttondown_class: "btn btn-classic btn-info",
    buttonup_class: "btn btn-classic btn-danger"
});

// Value attribute is not set (applying settings.initval)
$("input[name='demo3_21']").TouchSpin({
    initval: 40,
    buttondown_class: "btn btn-classic btn-primary",
    buttonup_class: "btn btn-classic btn-primary"
});

// Button postfix
$("input[name='demo4']").TouchSpin({
    postfix: "Button",
    postfix_extraclass: "btn btn-outline-info",
    buttondown_class: "btn btn-classic btn-primary",
    buttonup_class: "btn btn-classic btn-primary"
});

// Change button class
$("input[name='demo6']").TouchSpin({
    buttondown_class: "btn btn-classic btn-danger",
    buttonup_class: "btn btn-classic btn-success"
});