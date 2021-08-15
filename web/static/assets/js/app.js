var App = function() {
    var MediaSize = {
        xl: 1200,
        lg: 992,
        md: 991,
        sm: 576
    };
    var ToggleClasses = {
        headerhamburger: '.toggle-sidebar',
        inputFocused: 'input-focused',
    };

    var Selector = {
        mainHeader: '.header.navbar',
        headerhamburger: '.toggle-sidebar',
        fixed: '.fixed-top',
        mainContainer: '.main-container',
        sidebar: '#sidebar',
        sidebarContent: '#sidebar-content',
        sidebarStickyContent: '.sticky-sidebar-content',
        ariaExpandedTrue: '#sidebar [aria-expanded="true"]',
        ariaExpandedFalse: '#sidebar [aria-expanded="false"]',
        contentWrapper: '#content',
        contentWrapperContent: '.container',
        mainContentArea: '.main-content',
        searchFull: '.toggle-search',
        overlay: {
            sidebar: '.overlay',
            cs: '.cs-overlay',
            search: '.search-overlay'
        }
    };

    // Default Enabled

    var toggleFunction = {
        sidebar: function() {
            $('.sidebarCollapse').on('click', function (sidebar) {
                sidebar.preventDefault();
                $('body').toggleClass("topbar-closed");
                $('body').toggleClass("sbar-open");
                $('.overlay').toggleClass('show');
                $('html,body').toggleClass('sidebar-noneoverflow');
            });
        },
        overlay: function() {
            $('#dismiss, .overlay').on('click', function () {
                // hide sidebar
                $('body').removeClass('topbar-closed');
                // hide overlay
                $('.overlay').removeClass('show');
                $('html,body').removeClass('sidebar-noneoverflow');
            });
        },
        deactivateScroll: function() {
            const ps = new PerfectScrollbar('#topbar');
            ps.destroy();
        },
        search: function() {
            $(Selector.searchFull).click(function(event) {
                // console.log('dfdfdf')
               $(this).parents('.search-animated').find('.search-full').addClass(ToggleClasses.inputFocused);
               $(this).parents('.search-animated').addClass('show-search');
               $(Selector.overlay.search).addClass('show');
               $(Selector.overlay.search).addClass('show');
               $( ".search-form-control" ).focus();
            });

            $(Selector.overlay.search).click(function(event) {
               $(this).removeClass('show');
               $(Selector.searchFull).parents('.search-animated').find('.search-full').removeClass(ToggleClasses.inputFocused);
               $(Selector.searchFull).parents('.search-animated').removeClass('show-search');
            });
        }
    }

    var mobileFunctions = {
        activateScroll: function() {
            const ps = new PerfectScrollbar('#topbar', {
                wheelSpeed:.5,
                swipeEasing:!0,
                minScrollbarLength:40,
                maxScrollbarLength:300
            });
        },
    }
    var desktopFunctions = {
        activateScroll: function() {
            const desktopFncScroll = new PerfectScrollbar('.menu-categories li.menu .submenu', {
                wheelSpeed:.5,
                swipeEasing:!0,
                minScrollbarLength:40,
                maxScrollbarLength:300
            });
        },
        preventAccordionOnClick: function() {
            $('.menu > a[data-toggle="collapse"], .menu.single-menu  a[data-toggle="collapse"]').click(function(e){
                getWindowWidth = window.innerWidth;
                if (getWindowWidth > 991) {
                    e.preventDefault(); // to stop the page jump to the anchor target.
                    e.stopPropagation();
                }
            })
        }
    }

    var inBuiltfunctionality = {
        preventScrollBody: function() {
            $('#topbar').bind('mousewheel DOMMouseScroll', function(e) {
                var scrollTo = null;

                if (e.type == 'mousewheel') {
                    scrollTo = (e.originalEvent.wheelDelta * -1);
                }
                else if (e.type == 'DOMMouseScroll') {
                    scrollTo = 40 * e.originalEvent.detail;
                }

                if (scrollTo) {
                    e.preventDefault();
                    $(this).scrollTop(scrollTo + $(this).scrollTop());
                }
            });
        },
        closeDropdownDocumentClick: function() {
            $(document).click(function(event){
                $('.topbar-nav .collapse').collapse('hide')
            });
        },
        default: function() {
            $(document).scroll(function(event) {

              var elementMainContent = $('.main-content');
              var elementNavbar = $( '.topbar-nav');
              var sideNav = $('.sidenav');
              var elementOffset = elementMainContent.offset().top;
              var windowScroll = $(window).scrollTop();
              // Check if window scroll > or == element offset?
                if (windowScroll >= elementOffset) {
                    sideNav.css('top', '95px');
                } else if (windowScroll < elementOffset) {
                    sideNav.css('top', '147px');
                }

            });
        },
        languageDropdown: function() {
            var getDropdownElement = document.querySelectorAll('.more-dropdown .dropdown-item');
            for (var i = 0; i < getDropdownElement.length; i++) {
                getDropdownElement[i].addEventListener('click', function() {
                    document.querySelectorAll('.more-dropdown .dropdown-toggle > img')[0].setAttribute('src', 'assets/img/' + this.getAttribute('data-img-value') + '.png' );
                })
            }
        },
    }

    var _mobileResolution = {
        onRefresh: function() {
            var windowWidth = window.innerWidth;
            if ( windowWidth <= MediaSize.md ) {
                console.log('On Mobile Refresh');
                toggleFunction.search();
                mobileFunctions.activateScroll();
                $('.menu.active .collapse.submenu').addClass('show');
            }
        },
        onResize: function() {
            $(window).on('resize', function(event) {
                event.preventDefault();
                var windowWidth = window.innerWidth;
                if ( windowWidth <= MediaSize.md ) {
                    toggleFunction.search();
                    $('.menu.active .collapse.submenu').addClass('show');
                    console.log('On Mobile Resize');
                }
            });
        }
    }

    var _desktopResolution = {
        onRefresh: function() {
            var windowWidth = window.innerWidth;
            if ( windowWidth > MediaSize.md ) {
                toggleFunction.search();
                inBuiltfunctionality.closeDropdownDocumentClick();
                $('.menu.active .collapse.submenu').removeClass('show');
                console.log('On Desktop Refresh');
            }
        },
        onResize: function() {
            $(window).on('resize', function(event) {
                event.preventDefault();
                var windowWidth = window.innerWidth;
                if ( windowWidth > MediaSize.md ) {
                    toggleFunction.search();
                    toggleFunction.deactivateScroll();
                    inBuiltfunctionality.closeDropdownDocumentClick();
                    $('.menu.active .collapse.submenu').removeClass('show');
                    console.log('On Desktop Resize');
                }
            });
        }
    }

    return {
        init: function() {

            // Sidebar fn
            toggleFunction.sidebar();
            // Overlay fn
            toggleFunction.overlay();
            // Desktop Resoltion fn
            _desktopResolution.onRefresh();
            _desktopResolution.onResize();
            // Mobile Resoltion fn
            _mobileResolution.onRefresh();
            _mobileResolution.onResize();

            if (!$('body').hasClass('alt-menu')) {
                inBuiltfunctionality.default();
            }

            inBuiltfunctionality.languageDropdown();
        },
    }

}();
