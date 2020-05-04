$("#example-basic").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    autoFocus: true,
    cssClass: 'pill wizard'
});
$("#circle-basic").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    autoFocus: true,
    cssClass: 'circle wizard'
});
$("#example-vertical").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    cssClass: 'circle wizard',
    titleTemplate: '<span class="number">#index#</span>',
    stepsOrientation: "vertical"
});
$("#pill-vertical").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    cssClass: 'pills wizard',
    titleTemplate: '#title#',
    stepsOrientation: "vertical"
});