$(function() {

    /*
    =========================================
    |                                       |
    |          Variables Definations        |
    |                                       |
    =========================================
    */

    var Container = {
        scrumboard: $('.scrumboard'),
        card: $('.scrumboard .card')
    }

    // Containers
    var scrumboard = Container.scrumboard;
    var card = Container.card;


    // Make Task Sortable

    function $_taskSortable() {
        $('[data-sortable="true"]').sortable({
            connectWith: '.connect-sorting-content',
            items: ".card",
            cursor: 'move',
            placeholder: "ui-state-highlight",
            refreshPosition: true,
            stop: function( event, ui ) {
                var parent_ui = ui.item.parent().attr('data-section');

            },
            update: function( event, ui ) {
                console.log(ui);
                console.log(ui.item);
            }
        });
    }

    // Click on Add Task button to open the modal and more..

    function addTask() {
        $('.addTask').on('click', function(event) {
            event.preventDefault();
            getParentElement = $(this).parents('[data-connect="sorting"]').attr('data-section');
            $('.edit-task-title').hide();
            $('.add-task-title').show();
            $('[data-btnfn="addTask"]').show();
            $('[data-btnfn="editTask"]').hide();
            $('.addTaskAccordion .collapse').collapse('hide');
            $('#addTaskModal').modal('show');
            $_taskAdd(getParentElement);
        });
    }

    // Get the range count value

    $('#progress-range-counter').on('input', function(event) {
        event.preventDefault();
        /* Act on the event */
        getRangeValue = $(this).val();
        $('.range-count-number').html(getRangeValue);
        $('.range-count-number').attr('data-rangeCountNumber', getRangeValue);
    });

    // Reset the input Values

    $('#addTaskModal, #addListModal').on('hidden.bs.modal', function (e) {
        $('input,textarea').val('');
        $('input[type="range"]').val(0);
        $('.range-count-number').attr('data-rangecountnumber', 0);
        $('.range-count-number').html(0);
    })

    // change the modal Button class on accordion open 

    $('.addTaskAccordion .collapse').on('shown.bs.collapse', function () {

        getClassOfAccordion = $(this).parents('.card').attr('class').split(' ')[1];
        getClassOfAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').attr('class').split(' ')[1];
        removeClassOfAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').removeClass(getClassOfAddTaskBtn);
        var addClassInAddTaskBtn;

        if (getClassOfAccordion === 'task-simple') {
            addClassInAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').addClass('task-simple');
        }
        if (getClassOfAccordion === 'task-text-progress') {
            addClassInAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').addClass('task-text-progress');
        } else if (getClassOfAccordion === 'task-checkbox') {
            addClassInAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').addClass('task-checkbox');
        } else if (getClassOfAccordion === 'task-image') {
            addClassInAddTaskBtn = $(this).parents('.modal-content').find('[data-btnfn="addTask"]').addClass('task-image');
        }
    })

    function $_taskAdd( getParent ) {

        $('[data-btnfn="addTask"]').off('click').on('click', function(event) {

            getAddBtnClass = $(this).attr('class').split(' ')[1];

              var today = new Date();
              var dd = String(today.getDate()).padStart(2, '0');
              var mm = String(today.getMonth()); //January is 0!
              var yyyy = today.getFullYear();

              var monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ];

              today = dd + ' ' + monthNames[mm] + ', ' + yyyy;

            var $_getParent = getParent;

            if (getAddBtnClass === 'task-simple') {
                var $_task = document.getElementById('s-simple-task').value;

                $html =   '<div data-draggable="true" class="card simple-title-task" style="">'+
                                '<div class="card-body">'+

                                    '<div class="task-header">'+
                                        
                                        '<div class="">'+
                                            '<h4 class="" data-taskTitle="'+$_task+'">'+$_task+'</h4>'+
                                        '</div>'+

                                        '<div class="">'+
                                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-edit-2 s-task-edit"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg> '+
                                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-trash-2 s-task-delete"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'+
                                        '</div>'+

                                    '</div>'+

                                '</div>'+
                            '</div>';

                $("[data-section='"+$_getParent+"'] .connect-sorting-content").append($html); 

            } else if (getAddBtnClass === 'task-text-progress') {
                var $_task = document.getElementById('s-task').value;
                var $_taskText = document.getElementById('s-text').value;

                var $_taskProgress = $('.range-count-number').attr('data-rangeCountNumber');

                    $html = '<div data-draggable="true" class="card task-text-progress" style="">'+
                                '<div class="card-body">'+

                                    '<div class="task-header">'+
                                        
                                        '<div class="">'+
                                            '<h4 class="" data-taskTitle="'+ $_task +'">'+ $_task +'</h4>'+
                                        '</div>'+
                                        
                                        '<div class="">'+
                                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-edit-2 s-task-edit"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>'+
                                        '</div>'+

                                    '</div>'+

                                    '<div class="task-body">'+

                                        '<div class="task-content">'+
                                            '<p class="" data-taskText="'+ $_taskText +'">'+ $_taskText +'</p>'+

                                            '<div class="">'+
                                                '<div class="progress br-30">'+
                                                    '<div class="progress-bar bg-success" role="progressbar" data-progressState="'+$_taskProgress+'" style="width: '+$_taskProgress+'%" aria-valuenow="'+$_taskProgress+'" aria-valuemin="0" aria-valuemax="100"></div>'+
                                                '</div>'+

                                                '<p class="progress-count">'+$_taskProgress+'%</p>'+

                                            '</div>'+
                                        '</div>'+

                                        '<div class="task-bottom">'+
                                            '<div class="tb-section-1">'+
                                                '<span data-taskDate="'+today+'"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-calendar"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> '+today+'</span>'+
                                            '</div>'+
                                            '<div class="tb-section-2">'+
                                                '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-trash-2 s-task-delete"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'+
                                            '</div>'+
                                        '</div>'+
                                        
                                    '</div>'+

                                '</div>'+
                            '</div>';

                $("[data-section='"+$_getParent+"'] .connect-sorting-content").append($html); 

            } else if (getAddBtnClass === 'task-image') {
                var $_task = document.getElementById('s-image-task').value;

                $html =   '<div data-draggable="true" class="card img-task ui-sortable-handle" style="">'+
                                '<div class="card-body">'+

                                    '<div class="task-content">'+
                                        '<img src="assets/img/400x168.jpg" class="img-fluid">'+
                                    '</div>'+

                                    '<div class="task-header">'+
                                        
                                        '<div class="">'+
                                            '<h4 class="" data-tasktitle="'+ $_task +'">'+ $_task +'</h4>'+
                                        '</div>'+

                                        '<div class="">'+
                                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-edit-2 s-task-edit"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>'+
                                        '</div>'+

                                    '</div>'+

                                    '<div class="task-body">'+

                                        '<div class="task-bottom">'+
                                            '<div class="tb-section-1">'+
                                                '<span data-taskdate="'+today+'"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-calendar"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> '+today+'</span>'+
                                            '</div>'+
                                            '<div class="tb-section-2">'+
                                                '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-trash-2 s-task-delete"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'+
                                            '</div>'+
                                        '</div>'+
                                        
                                    '</div>'+
                                '</div>'+
                            '</div>';

                $("[data-section='"+$_getParent+"'] .connect-sorting-content").append($html);
            }

            $('#addTaskModal').modal('hide');

            $_taskEdit();
            $_taskDelete();
        });
    }

    $("#add-list").off('click').on('click', function(event) {
      event.preventDefault();

        $('.add-list').show();
        $('.edit-list').hide();
        $('.edit-list-title').hide();
        $('.add-list-title').show();
        $('#addListModal').modal('show');
    });

    $(".add-list").off('click').on('click', function(event) {
        var today = new Date();
        var dd = String(today.getDate()).padStart(2, '0');
        var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        var yyyy = today.getFullYear();

        today = mm + '.' + dd + '.' + yyyy;

        var $_listTitle = document.getElementById('s-list-name').value;

        var $_listTitleLower = $_listTitle.toLowerCase();
        var $_listTitleRemoveWhiteSpaces = $_listTitleLower.split(' ').join('_') ;
        var $_listSectionDataAttr = $_listTitleRemoveWhiteSpaces;


        $html = '<div data-section="s-'+$_listSectionDataAttr+'" class="task-list-container  mb-4 " data-connect="sorting">'+
                    '<div class="connect-sorting">'+
                        '<div class="task-container-header">'+
                            '<h6 class="s-heading" data-listTitle="'+$_listTitle+'">'+$_listTitle+'</h6>'+
                            '<div class="dropdown">'+
                                '<a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink-4" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">'+
                                    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-more-horizontal"><circle cx="12" cy="12" r="1"></circle><circle cx="19" cy="12" r="1"></circle><circle cx="5" cy="12" r="1"></circle></svg>'+
                                '</a>'+
                                '<div class="dropdown-menu dropdown-menu-right" aria-labelledby="dropdownMenuLink-4">'+
                                    '<a class="dropdown-item list-edit" href="javascript:void(0);">Edit</a>'+
                                    '<a class="dropdown-item list-delete" href="javascript:void(0);">Delete</a>'+
                                    '<a class="dropdown-item list-clear-all" href="javascript:void(0);">Clear All</a>'+
                                '</div>'+
                            '</div>'+
                        '</div>'+

                        '<div class="connect-sorting-content" data-sortable="true">'+
                            
                            
                        '</div>'+

                        '<div class="add-s-task">'+
                            '<a class="addTask"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-plus-circle"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg> Add Task</a>'+
                        '</div>'+

                    '</div>'+
                '</div>';

        $(".task-list-section").append($html); 
        $('#addListModal').modal('hide');
        $('#s-list-name').val('');
        $_taskSortable();
        $_editList()
        $_deleteList();
        $_clearList();
        addTask();
        $_taskEdit();
        $_taskDelete();
    })

    // Delete the whole list including tasks at on click

    function $_deleteList() {
        $('.list-delete').off('click').on('click', function(event) {
            event.preventDefault();
            $(this).parents('[data-connect]').remove();
        })
    }
    function $_editList() {
        $('.list-edit').off('click').on('click', function(event) {

            event.preventDefault();

            var $_outerThis = $(this);
           
            $('.add-list').hide();
            $('.edit-list').show();

            $('.add-list-title').hide();
            $('.edit-list-title').show();

            var $_listTitle = $_outerThis.parents('[data-connect="sorting"]').find('.s-heading').attr('data-listTitle');
            $('#s-list-name').val($_listTitle);

            $('.edit-list').off('click').on('click', function(event) {
                var $_innerThis = $(this);
                var $_getListTitle = document.getElementById('s-list-name').value;

                var $_editedListTitle = $_outerThis.parents('[data-connect="sorting"]').find('.s-heading').html($_getListTitle);
                var $_editedListTitleDataAttr = $_outerThis.parents('[data-connect="sorting"]').find('.s-heading').attr('data-listTitle', $_getListTitle);

                $('#addListModal').modal('hide');
                $('#s-list-name').val('');
            })
            $('#addListModal').modal('show');
            $('#addListModal').on('hidden.bs.modal', function (e) {
                $('#s-list-name').val('');
            })
        })
    }

    // Clear all task at on click

    function $_clearList() {
        $('.list-clear-all').off('click').on('click', function(event) {
            event.preventDefault();
            $(this).parents('[data-connect="sorting"]').find('.connect-sorting-content .card').remove();
        })
    }

    // Delete the task on click 

    function $_taskDelete() {
        $('.card .s-task-delete').off('click').on('click', function(event) {
            event.preventDefault();

            get_card_parent = $(this).parents('.card');

            $('#deleteConformation').modal('show');

            $('[data-remove="task"]').on('click', function(event) {
                event.preventDefault();
                /* Act on the event */
                get_card_parent.remove();
                $('#deleteConformation').modal('hide');
            });

        })
    }

    function $_taskEdit() {
      $('.card .s-task-edit').off('click').on('click', function(event) {

        event.preventDefault();

        var $_outerThis = $(this);
       
        $('.add-task-title').hide();
        $('.edit-task-title').show();

        $('[data-btnfn="addTask"]').hide();
        $('[data-btnfn="editTask"]').show();

        if ($(this).parents('.card').hasClass('img-task')) {

            var $_taskTitle = $_outerThis.parents('.card').find('h4').attr('data-taskTitle');
            var get_value_title = $('.task-image #s-image-task').val($_taskTitle);
            $('.task-image .collapse').collapse('show');

        } else if ($(this).parents('.card').hasClass('simple-title-task')) {

            var $_taskTitle = $_outerThis.parents('.card').find('h4').attr('data-taskTitle');
            var get_value_title = $('.task-simple #s-simple-task').val($_taskTitle);
            $('.task-simple .collapse').collapse('show');

        } else if ($(this).parents('.card').hasClass('task-text-progress')) {

            var $_taskTitle = $_outerThis.parents('.card').find('h4').attr('data-taskTitle');
            var get_value_title = $('.task-text-progress #s-task').val($_taskTitle);

            var $_taskText = $_outerThis.parents('.card').find('p:not(".progress-count")').attr('data-taskText');
            var get_value_text = $('.task-text-progress #s-text').val($_taskText);

            var $_taskProgress = $_outerThis.parents('.card').find('div.progress-bar').attr('data-progressState');
            var get_value_progress = $('#progress-range-counter').val($_taskProgress);
            var get_value_progressHtml = $('.range-count-number').html($_taskProgress);
            var get_value_progressDataAttr = $('.range-count-number').attr('data-rangecountnumber', $_taskProgress);

            $('.task-text-progress .collapse').collapse('show');
        }

        $('[data-btnfn="editTask"]').off('click').on('click', function(event) {
            var $_innerThis = $(this);

            if ($_outerThis.parents('.card').hasClass('img-task')) {

                var $_task = document.getElementById('s-image-task').value;
                var $_taskDataAttr = $_outerThis.parents('.card').find('h4').attr('data-taskTitle' , $_task);
                var $_taskTitle = $_outerThis.parents('.card').find('h4').html($_task);

            } else if ($_outerThis.parents('.card').hasClass('simple-title-task')) {

                var $_task = document.getElementById('s-simple-task').value;
                var $_taskDataAttr = $_outerThis.parents('.card').find('h4').attr('data-taskTitle' , $_task);
                var $_taskTitle = $_outerThis.parents('.card').find('h4').html($_task);

            } else if ($_outerThis.parents('.card').hasClass('task-text-progress')) {

                var $_taskValue = document.getElementById('s-task').value;
                var $_taskTextValue = document.getElementById('s-text').value;
                var $_taskProgressValue = $('.range-count-number').attr('data-rangeCountNumber');

                var $_taskDataAttr = $_outerThis.parents('.card').find('h4').attr('data-taskTitle' , $_taskValue);
                var $_taskTitle = $_outerThis.parents('.card').find('h4').html($_taskValue);
                var $_taskTextDataAttr = $_outerThis.parents('.card').find('p:not(".progress-count")').attr('data-tasktext' , $_taskTextValue);
                var $_taskText = $_outerThis.parents('.card').find('p:not(".progress-count")').html($_taskTextValue);

                var $_taskProgressStyle = $_outerThis.parents('.card').find('div.progress-bar').attr('style', "width: " + $_taskProgressValue +"%");
                var $_taskProgressDataAttr = $_outerThis.parents('.card').find('div.progress-bar').attr('data-progressState', $_taskProgressValue);
                var $_taskProgressAriaAttr = $_outerThis.parents('.card').find('div.progress-bar').attr('aria-valuenow', $_taskProgressValue);
                var $_taskProgressProgressCount = $_outerThis.parents('.card').find('.progress-count').html($_taskProgressValue+"%");
            }

            $('#addTaskModal').modal('hide');
            var setDate = $('.taskDate').html('');
            $('.taskDate').hide();
        })
        $('#addTaskModal').modal('show');
      })
    }

$_editList();
$_deleteList();
$_clearList();
addTask();
$_taskEdit();
$_taskDelete();
$_taskSortable();

});