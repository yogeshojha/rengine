// Default

$('.default').click(function() {
   Snackbar.show({text: 'Example notification text.', duration: 100000});
});

// Position

$('.top-left').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'top-left'
    });
});

$('.top-center').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'top-center'
    });
});

$('.top-right').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'top-right'
    });
});

$('.bottom-left').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'bottom-left'
    });
});

$('.bottom-center').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'bottom-center'
    });
});

$('.bottom-right').click(function() {
    Snackbar.show({
        text: 'Example notification text.',
        pos: 'bottom-right'
    });
});


// Action Button

$('.no-action').click(function() {
    Snackbar.show({
        showAction: false
    });
});

// Action Text

$('.action-text').click(function() {
    Snackbar.show({
        actionText: 'Thanks!'
    });
});

// Text Color

$('.text-color').click(function() {
    Snackbar.show({
        actionTextColor: '#e2a03f',
    });
});

// Click Callback
$('.click-callback').click(function() {
    Snackbar.show({
        text: 'Custom callback when action button is clicked.',
        width: 'auto',
        onActionClick: function(element) {
            //Set opacity of element to 0 to close Snackbar 
            $(element).css('opacity', 0);
            Snackbar.show({
                text: 'Thanks for clicking the  <strong>Dismiss</strong>  button!',
                showActionButton: false
            });
        }
    });
});

// Duration

$('.duration').click(function() {
    Snackbar.show({
        text: 'Duration set to 5s',
        duration: 5000,
    });
});

// Custom Background

$('.snackbar-bg-primary').click(function() {
    Snackbar.show({
        text: 'Primary',
        actionTextColor: '#fff',
        backgroundColor: '#1b55e2'
    });
});

$('.snackbar-bg-info').click(function() {
    Snackbar.show({
        text: 'Info',
        actionTextColor: '#fff',
        backgroundColor: '#2196f3'
    });
});

$('.snackbar-bg-success').click(function() {
    Snackbar.show({
        text: 'Success',
        actionTextColor: '#fff',
        backgroundColor: '#8dbf42'
    });
});

$('.snackbar-bg-warning').click(function() {
    Snackbar.show({
        text: 'Warning',
        actionTextColor: '#fff',
        backgroundColor: '#e2a03f'
    });
});

$('.snackbar-bg-danger').click(function() {
    Snackbar.show({
        text: 'Danger',
        actionTextColor: '#fff',
        backgroundColor: '#e7515a'
    });
});

$('.snackbar-bg-dark').click(function() {
    Snackbar.show({
        text: 'Dark',
        actionTextColor: '#fff',
        backgroundColor: '#3b3f5c'
    });
});