(function ($) {

  'use strict';

  /*jslint browser:true */
  /*jslint devel:true */
  /*global $, jQuery, alert, console*/

  $.fn.xpanda = function (settings) {

    // Default settings.
    var self = this,
    defaults = $.extend(true, {
      breakpoints: {
        xs: {
          minWidth: 0,
          itemsPerRow: 2
        },
        sm: {
          minWidth: 576,
          itemsPerRow: 4
        },
        md: {
          minWidth: 768,
          itemsPerRow: 6
        },
        lg: {
          minWidth: 992,
          itemsPerRow: 8
        },
        xl: {
          minWidth: 1200,
          itemsPerRow: 10
        },
        xx: {
          minWidth: 1400,
          itemsPerRow: 12
        }
      },
      element: {
        selector: '.x-item',
        equalThumbSizes: true,
        wrapperClass: 'x-item-wrap',
        toClone: '.x-content',
        spaceBetweenItems: 10,
        spaceBetweenRows: 10
      },
      placeholder: {
        class: 'x-placeholder',
        marginSides: 10,
        desktopScrollTo: true,
        scrollSpeed: 400,
        scrollTopOffset: 0,
        slideAnimation: true,
        slideSpeed: 400,
        showControls: true
      },
      spacer: {
        class: 'x-spacer-inside'
      },
      independent: true,
      history: false
    }, settings);

    return self.each(function () {

      // Namespace.
      var APP = {};

      // Sub namespace functions.
      APP.GO = {

        // Global variables.
        globalVar: function () {

          // Fixed.
          APP.GO.win = $(window);
          APP.GO.doc = $(document);
          APP.GO.html = $('html');
          APP.GO.userAgent = navigator.userAgent;

          APP.GO.container = self; // container
          APP.GO.spacer = $('.x-spacer-outside'); // spacer

          APP.GO.item = APP.GO.container.find(String(defaults.element.selector)); // item
          APP.GO.itemLength = APP.GO.item.length; // item length

          // Dynamic.
          APP.GO.winWidth = APP.GO.win.width(); // window width
          APP.GO.winHeight = APP.GO.win.height(); // window height
          APP.GO.winTop = APP.GO.win.scrollTop(); // window scroll top

          APP.GO.containerWidth = APP.GO.container.width(); // container width
          APP.GO.containerWidthCached = APP.GO.container.width(); // cached container width
          APP.GO.columnCount = 0; // columns
          APP.GO.updatedColumnCount = 0; // updated columns
          APP.GO.placeholderCount = 1; // placeholders

          APP.GO.throttleResizeFunc = _.throttle(APP.GO.updateResizeThrottle, 1);
          APP.GO.throttleScrollFunc = _.throttle(APP.GO.updateScrollThrottle, 10);

        },

        // Initial load.
        initialLoad: function () {

          // variables
          var uaString = APP.GO.userAgent.toLowerCase();

          // check if mobile device
          APP.GO.isMobileDevice = (uaString.match(/ipad|iphone|android|iemobile/g)) ? true : false;

          // get first instance and assign active state for keyboard navigation
          $('.xpanda[data-instance="1"]').addClass('x-keyboard-active');

          // change keyboard active state on click
          $('.xpanda').on('click', function () {
            $(this).addClass('x-keyboard-active').siblings('.xpanda').removeClass('x-keyboard-active');
          });

          // do we need to fix the width?
          APP.GO.fixWidth = (APP.GO.container.hasClass('x-fix-width')) ? true : false;

          // add x-initiated class to main selector and spacer html
          APP.GO.container.addClass('x-initiated');
          APP.GO.spacer.addClass('x-initiated');

          // get jquery version
          APP.GO.jqueryVersion = $.fn.jquery.split('.')[0];

        },

        // Destroy preloader.
        destroyPreloader: function () {

          APP.GO.container.each(function () {

            // variables
            var $self = $(this);

            if ($self.hasClass('x-preloader')) {
              $self.removeClass('x-preloader').promise().then(function () {
                setTimeout(function () {
                  APP.GO.lazyLoadThumb();
                }, 10);
              });
            }

          });

        },

        // Get column count.
        getColumns: function () {

          if (APP.GO.containerWidth > defaults.breakpoints.xx.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.xx.itemsPerRow;
          } else if (APP.GO.containerWidth <= defaults.breakpoints.xx.minWidth && APP.GO.containerWidth > defaults.breakpoints.xl.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.xl.itemsPerRow;
          } else if (APP.GO.containerWidth <= defaults.breakpoints.xl.minWidth && APP.GO.containerWidth > defaults.breakpoints.lg.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.lg.itemsPerRow;
          } else if (APP.GO.containerWidth <= defaults.breakpoints.lg.minWidth && APP.GO.containerWidth > defaults.breakpoints.md.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.md.itemsPerRow;
          } else if (APP.GO.containerWidth <= defaults.breakpoints.md.minWidth && APP.GO.containerWidth > defaults.breakpoints.sm.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.sm.itemsPerRow;
          } else if (APP.GO.containerWidth <= defaults.breakpoints.sm.minWidth && APP.GO.containerWidth > defaults.breakpoints.xs.minWidth) {
            APP.GO.columnCount = defaults.breakpoints.xs.itemsPerRow;
          } else {
            console.log('error with breakpoints');
          }

        },

        // Create placeholders.
        createPlaceholders: function () {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this),
            thisInstanceItem = thisInstance.find(defaults.element.selector),
            thisInstanceItemLength = thisInstanceItem.length;

            // get column count
            APP.GO.updatedColumnCount = APP.GO.columnCount;

            // reset placeholder count
            APP.GO.placeholderCount = 1;

            thisInstanceItem.each(function () {

              // variables
              var $self = $(this),
              itemIndex = thisInstanceItem.index($self),
              remainder = itemIndex % APP.GO.updatedColumnCount,
              dataUntil = APP.GO.updatedColumnCount * APP.GO.placeholderCount,
              indicator = '<div class="x-indicator"></div>',
              placeholderMarkup = $('<div class="' + defaults.placeholder.class + '" data-until="' + dataUntil + '">').prepend(indicator).append('<div class="' + defaults.placeholder.class + '-inner" style="top: ' + defaults.element.spaceBetweenRows + 'px;"></div>'),
              horiMargins = (APP.GO.fixWidth) ? 0 : (defaults.element.spaceBetweenItems / 2);

              // assign data-index and data-group attributes
              $self.attr('data-index', itemIndex + 1).attr('data-group', dataUntil);

              // insert placeholders after each last item per row
              if (remainder === (APP.GO.updatedColumnCount - 1) || itemIndex === (thisInstanceItemLength - 1)) {

                $self.after(placeholderMarkup);

                // wrap all items
                thisInstance.find(defaults.element.selector + '[data-group="' + dataUntil + '"]').wrapAll('<div data-columns="' + APP.GO.updatedColumnCount + '" class="' + defaults.element.wrapperClass + '" style="margin: 0 ' + horiMargins + 'px"></div>');

                APP.GO.placeholderCount = APP.GO.placeholderCount + 1;

              }

            });

            APP.GO.createButtons(false);
            APP.GO.onArrowClick();
            APP.GO.onCloseClick();

          });

        },

        // Destroy placeholders.
        destroyPlaceholders: function () {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this),
            thisInstanceItem = thisInstance.find(defaults.element.selector);

            // unwrap items and remove placeholders
            thisInstanceItem.unwrap();
            thisInstance.find('.' + defaults.placeholder.class).remove().removeAttr('style');

          });

        },

        // Style items.
        styleItems: function () {

          APP.GO.item.each(function () {

            // variables
            var $self = $(this),
            thisIndex = $self.attr('data-index'),
            img = $self.find('img'),
            iWidth = img.width(), // for flex calculation
            iHeight = img.height(), // for flex calculation
            flexValue = iWidth / iHeight, // calculate flex basis
            hori = (defaults.element.spaceBetweenItems / 2) + 'px', // calculate horizontal margins
            firstAndLastHori = (APP.GO.fixWidth) ? 0 : hori, // horizontal margins for first and last item
            vert = defaults.element.spaceBetweenRows + 'px'; // calculate vertical margins

            // determine flex values
            if (APP.GO.updatedColumnCount === 1 || defaults.element.equalThumbSizes === true) {
              $self.css({'flex-grow': 1});
            } else {
              $self.css({'flex-grow': flexValue});
            }

            $self.css({
              'flex-shrink': 1,
              'flex-basis': '0%',
              'margin-top': vert,
              'margin-bottom': 0
            });

            if (thisIndex % APP.GO.updatedColumnCount === 0) {
              // last child
              $self.css({
                'margin-right': firstAndLastHori,
                'margin-left': hori
              });
            } else if (thisIndex % APP.GO.updatedColumnCount - 1 === 0) {
              // first child
              $self.css({
                'margin-right': hori,
                'margin-left': firstAndLastHori
              });
            } else {
              // all other
              $self.css({
                'margin-right': hori,
                'margin-left': hori
              });
            }

          }).promise().then(function () {
            APP.GO.createSpacer();
          });

          // adding bottom margin
          APP.GO.container.css('margin-bottom', defaults.element.spaceBetweenRows);

        },

        // Create spacer.
        createSpacer: function () {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this),
            thisDataInstance = thisInstance.attr('data-instance'),
            originalSpacer = $('.x-spacer-outside[data-instance="' + thisDataInstance + '"]'),
            createdSpacer = $('.' + defaults.spacer.class + '[data-instance="' + thisDataInstance + '"]'),
            thisInstanceItem = thisInstance.find(defaults.element.selector),
            thisInstanceItemLength = thisInstanceItem.length;

            // hide original spacer
            originalSpacer.hide();

            // remove previously created spacer
            createdSpacer.remove();

            thisInstanceItem.each(function () {

              // variables
              var itemIndex = thisInstanceItem.index(this),
              lastPlaceholderUntil = thisInstance.find('.' + defaults.placeholder.class).last().attr('data-until'),
              lastRowItems = thisInstance.find(defaults.element.selector + '[data-group="' + lastPlaceholderUntil + '"]'),
              lastRowItemsLength = lastRowItems.length,
              spacesToFill = APP.GO.columnCount - lastRowItemsLength,
              paddingFix = ((spacesToFill - 1) * defaults.element.spaceBetweenItems) / 2,
              lastRow = thisInstance.find('.' + defaults.element.wrapperClass).last(),
              appendedMarginRight = (APP.GO.fixWidth) ? 0 : (defaults.element.spaceBetweenItems / 2),
              originalWidth = (APP.GO.fixWidth) ? APP.GO.containerWidth : APP.GO.containerWidth - (defaults.element.spaceBetweenItems * 2),
              originalMargins = (APP.GO.fixWidth) ? 0 : defaults.element.spaceBetweenItems,
              spacerMarkup = $('<div/>', {'class': defaults.spacer.class}).css({
                'flex-grow': spacesToFill,
                'flex-shrink': 1,
                'flex-basis': '0%',
                'margin-top': defaults.element.spaceBetweenRows + 'px',
                'margin-left': (defaults.element.spaceBetweenItems / 2),
                'margin-right': appendedMarginRight,
                'padding-left': paddingFix,
                'padding-right': paddingFix
              }).attr('data-instance', thisDataInstance);

              // create spacer with styles if item length of last row not equal to column count
              if (itemIndex === (thisInstanceItemLength - 1)) {

                // append to last row
                if (lastRowItemsLength < APP.GO.columnCount) {
                  spacerMarkup.appendTo(lastRow);
                } else {
                  originalSpacer.show().css({
                    'width': originalWidth + 'px',
                    'margin-left': originalMargins + 'px',
                    'margin-right': originalMargins + 'px',
                    'margin-bottom': defaults.element.spaceBetweenRows + 'px'
                  });
                }

              }

            });

          }).promise().then(function () {
            APP.GO.addSpacerContent();
          });

        },

        // Add content to spacer.
        addSpacerContent: function () {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this),
            thisDataInstance = thisInstance.attr('data-instance'),
            spacerWrap = $('.x-spacer-outside[data-instance="' + thisDataInstance + '"]'),
            spacerContent = spacerWrap.html();

            function isEmpty(el) {
              return !$.trim(el.html());
            }

            if (isEmpty(spacerWrap)) {
              // add empty class
              thisInstance.find('.' + defaults.spacer.class).addClass('x-spacer-empty');
            } else {
              // insert content
              thisInstance.find('.' + defaults.spacer.class).html(spacerContent);
            }

          }).promise().then(function () {
            APP.GO.destroyPreloader();
            APP.GO.lazyLoadThumb();
          });

        },

        // Trigger on resize (throttle).
        updateResizeThrottle: function () {

          // Dynamic.
          APP.GO.containerWidth = APP.GO.container.width(); // container width

          APP.GO.container.each(function () {

            // Variables.
            var thisInstance = $(this),
            currentActive = thisInstance.find('.x-is-active'),
            dataIndex = currentActive.attr('data-index'),
            thisInstanceInner = thisInstance.find('.' + defaults.placeholder.class + '-inner'),
            placeholder = thisInstance.find('.' + defaults.placeholder.class);

            // reset placeholder inner to flex (caused by adjustXpanda)
            thisInstanceInner.css({'display': ''});

            // If column count has changed.
            if (APP.GO.updatedColumnCount !== APP.GO.columnCount) {

              APP.GO.destroyPlaceholders();
              APP.GO.createPlaceholders();
              APP.GO.styleItems();

            } else {

              if (placeholder.hasClass('x-is-expanded')) {
                thisInstance.find('.x-is-expanded > .x-placeholder-inner').css('height', 'auto');
              }

              // update spacer
              APP.GO.createSpacer();

            }

            // If item was expanded before the resize.
            if (currentActive.length > 0) {

              if (APP.GO.containerWidth !== APP.GO.containerWidthCached) {

                // Dynamic.
                APP.GO.containerWidthCached = APP.GO.container.width(); // update cached container width

                // clear content
                thisInstance.find('.x-is-expanded > .x-placeholder-inner').find('.x-asset, .x-info, .x-updated-content').remove();

                // keep open current active item
                APP.GO.openXpanda(currentActive, dataIndex, false, false, false);

              }

              // add placeholder styles
              APP.GO.styleActivePlaceholder();

            }

            // Update column count.
            APP.GO.getColumns();

          });

        },

        // Trigger on scroll (throttle).
        updateScrollThrottle: function () {

          // Dynamic.
          APP.GO.winHeight = APP.GO.win.height(); // window height
          APP.GO.winTop = APP.GO.win.scrollTop(); // window scroll top

          APP.GO.lazyLoadThumb();

        },

        // On item click.
        onItemClick: function () {

          APP.GO.item.on('click', function (e) {

            e.preventDefault();

            // settings + variables
            var slide = defaults.placeholder.slideAnimation,
            scroll = defaults.placeholder.desktopScrollTo,
            indi = defaults.independent,
            $self = $(this),
            historyPath = $self.attr('data-path'),
            instanceSiblings = $self.closest('.xpanda').find(defaults.element.selector),
            allSiblings = $('.xpanda').find(defaults.element.selector),
            instanceActiveSibling = $self.closest('.xpanda').find('.x-is-active'),
            allActiveSibling = $('.xpanda').find('.x-is-active'),
            selfIndex = $self.attr('data-index'),
            instanceSiblingIndex = instanceActiveSibling.attr('data-index'),
            allSiblingIndex = allActiveSibling.attr('data-index'),
            selfGroup = $self.attr('data-group'),
            instanceSiblingGroup = instanceActiveSibling.attr('data-group');

            // clear history pushState funuction
            function clearHistory() {
              var url = window.location.href.toString(),
              query = window.location.search.toString();

              if (query.includes('?xpnd=')) {
                var originalUrl = url.split('?xpnd=')[0];
              } else {
                var originalUrl = url.split('&xpnd=')[0];
              }

              history.replaceState(null, null, originalUrl);
            }

            // toggles
            if ($self.hasClass('x-is-active')) {

              // remove state classes
              if (indi === false) {
                allSiblings.removeClass('x-is-not-active');
              } else {
                instanceSiblings.removeClass('x-is-not-active');
              }
              $self.removeClass('x-is-active');

              if (slide === true) {
                APP.GO.closeXpanda($self, selfIndex, true);
              } else {
                APP.GO.closeXpanda($self, selfIndex, false);
              }

              // clear history state
              if (defaults.history) {
                clearHistory();
              }

            } else {

              // toggle state classes
              if (indi === false) {
                allSiblings.removeClass('x-is-active').addClass('x-is-not-active');
              } else {
                instanceSiblings.removeClass('x-is-active').addClass('x-is-not-active');
              }
              $self.removeClass('x-is-not-active').addClass('x-is-active');

              if (instanceActiveSibling.length > 0 || allActiveSibling.length > 0) {
                if (selfGroup === instanceSiblingGroup) {
                  if (slide === true) {
                    APP.GO.adjustXpanda($self, instanceActiveSibling, selfIndex, true);
                  } else {
                    APP.GO.adjustXpanda($self, instanceActiveSibling, selfIndex, false);
                  }
                } else {
                  if (slide === true) {
                    if (scroll === true && APP.GO.isMobileDevice === false) {
                      if (indi === false) {
                        APP.GO.closeXpanda(allActiveSibling, allSiblingIndex, true);
                      } else {
                        APP.GO.closeXpanda(instanceActiveSibling, instanceSiblingIndex, true);
                      }
                      setTimeout(function () {
                        APP.GO.openXpanda($self, selfIndex, true, true);
                      }, defaults.placeholder.slideSpeed + 50);
                    } else {
                      if (indi === false) {
                        APP.GO.closeXpanda(allActiveSibling, allSiblingIndex, true);
                      } else {
                        APP.GO.closeXpanda(instanceActiveSibling, instanceSiblingIndex, true);
                      }
                      setTimeout(function () {
                        APP.GO.openXpanda($self, selfIndex, true, false, true);
                      }, defaults.placeholder.slideSpeed + 50);
                    }
                  } else {
                    if (indi === false) {
                      APP.GO.closeXpanda(allActiveSibling, allSiblingIndex, false);
                    } else {
                      APP.GO.closeXpanda(instanceActiveSibling, instanceSiblingIndex, false);
                    }
                    if (scroll === true && APP.GO.isMobileDevice === false) {
                      APP.GO.openXpanda($self, selfIndex, false, true, true);
                    } else {
                      APP.GO.openXpanda($self, selfIndex, false, false, true);
                    }
                  }
                }
              } else {
                if (slide === true) {
                  if (scroll === true && APP.GO.isMobileDevice === false) {
                    APP.GO.openXpanda($self, selfIndex, true, true, false);
                  } else {
                    APP.GO.openXpanda($self, selfIndex, true, false, false);
                  }
                } else {
                  if (scroll === true && APP.GO.isMobileDevice === false) {
                    APP.GO.openXpanda($self, selfIndex, false, true, false);
                  } else {
                    APP.GO.openXpanda($self, selfIndex, false, false, false);
                  }
                }
              }

              // clear history state then push
              if (defaults.history) {
                clearHistory();
                var query = window.location.href.indexOf('?') === -1 ? '?xpnd=' : '&xpnd=';
                history.pushState(null, null, window.location.href + query + historyPath);
              }

            }

          });

        },

        // Open xpanda.
        openXpanda: function (target, index, slide, scroll, sibling) {

          // variables
          var content = target.find(defaults.element.toClone).html(),
          closestInstance = target.closest('.xpanda'),
          ceiling = Math.ceil(index / APP.GO.updatedColumnCount) * APP.GO.updatedColumnCount,
          cloneDestination = closestInstance.find('.' + defaults.placeholder.class + '[data-until="' + ceiling + '"]'),
          cloneDestinationInner = cloneDestination.find('.' + defaults.placeholder.class + '-inner'),
          placeholderTop = defaults.element.spaceBetweenRows,
          scrollTopOffset = defaults.placeholder.scrollTopOffset;

          // add active placeholder class and clone content
          cloneDestination.addClass('x-is-expanded');
          cloneDestinationInner.prepend(content).promise().then(function () {

            if (APP.GO.jqueryVersion < 3) {
              APP.GO.styleActivePlaceholder();
            }

            // reset placeholder inner height to get an accurate reading
            cloneDestinationInner.css({height: 'auto', top: placeholderTop}).promise().then(function () {

              // get adjusted placeholder height
              var adjustedHeight = cloneDestinationInner.outerHeight();

              // expand them now
              if (sibling === true) {
                if (slide === true) {
                  cloneDestinationInner.animate({height: adjustedHeight});
                  cloneDestination.animate({height: adjustedHeight + defaults.element.spaceBetweenRows}, defaults.placeholder.slideSpeed, 'linear').promise().then(function () {
                    cloneDestinationInner.animate({opacity: 1}).promise().then(function () {
                      if (scroll === true) {
                        $('html, body').animate({ scrollTop: target.parent('.x-item-wrap').offset().top - scrollTopOffset }, defaults.placeholder.scrollSpeed, 'linear');
                        APP.GO.showIndicator(target, 100);
                      } else {
                        APP.GO.showIndicator(target, 0);
                      }
                    });
                  });
                } else {
                  cloneDestination.css({height: adjustedHeight + defaults.element.spaceBetweenRows});
                  cloneDestinationInner.css({height: adjustedHeight, opacity: 1}).promise().then(function () {
                    if (scroll === true) {
                      $('html, body').animate({ scrollTop: target.parent('.x-item-wrap').offset().top - scrollTopOffset }, defaults.placeholder.scrollSpeed, 'linear');
                      APP.GO.showIndicator(target, 400);
                    } else {
                      APP.GO.showIndicator(target, 200);
                    }
                  });
                }
              } else {
                if (slide === true) {
                  cloneDestinationInner.animate({height: adjustedHeight});
                  cloneDestination.animate({height: adjustedHeight + defaults.element.spaceBetweenRows}, defaults.placeholder.slideSpeed, 'linear').promise().then(function () {
                    cloneDestinationInner.animate({opacity: 1}).promise().then(function () {
                      if (scroll === true) {
                        $('html, body').animate({ scrollTop: target.parent('.x-item-wrap').offset().top - scrollTopOffset }, defaults.placeholder.scrollSpeed, 'linear');
                        APP.GO.showIndicator(target, 0);
                      } else {
                        APP.GO.showIndicator(target, 0);
                      }
                    });
                  });
                } else {
                  cloneDestination.css({height: adjustedHeight + defaults.element.spaceBetweenRows});
                  cloneDestinationInner.css({height: adjustedHeight, opacity: 1}).promise().then(function () {
                    if (scroll === true) {
                      $('html, body').animate({ scrollTop: target.parent('.x-item-wrap').offset().top - scrollTopOffset }, defaults.placeholder.scrollSpeed, 'linear');
                      APP.GO.showIndicator(target, 400);
                    } else {
                      APP.GO.showIndicator(target, 200);
                    }
                  });
                }
              }

            });

            if (APP.GO.jqueryVersion >= 3) {
              APP.GO.styleActivePlaceholder();
            }
            APP.GO.lazyLoadAsset(index);
            APP.GO.updateButtons(index, ceiling);

          });

        },

        // Close xpanda.
        closeXpanda: function (target, index, slide) {

          // variables
          var closestInstance = target.closest('.xpanda'),
          ceiling = Math.ceil(index / APP.GO.updatedColumnCount) * APP.GO.updatedColumnCount,
          cloneDestination = closestInstance.find('.' + defaults.placeholder.class + '.x-is-expanded'),
          cloneDestinationInner = cloneDestination.find('.' + defaults.placeholder.class + '-inner');

          // hide indicator
          APP.GO.hideIndicator();

          if (slide === true) {
            cloneDestination.animate({height: 0}, defaults.placeholder.slideSpeed, 'linear').promise().then(function () {
              cloneDestination.removeClass('x-is-expanded').removeAttr('style');
            });
            cloneDestinationInner.animate({height: 0, opacity: 0}, defaults.placeholder.slideSpeed, 'linear').promise().then(function () {
              cloneDestinationInner.removeAttr('style').find('.x-asset, .x-info, .x-updated-content').remove();
            });
          } else {
            cloneDestination.removeClass('x-is-expanded').removeAttr('style');
            cloneDestinationInner.removeAttr('style').css({opacity: 0}).find('.x-asset, .x-info, .x-updated-content').remove();
          }

          // callbacks
          APP.GO.lazyLoadThumb();

        },

        // Adjust xpanda.
        adjustXpanda: function (target, targetSibling, targetIndex, slide) {

          // variables
          var content = target.find(defaults.element.toClone).html(),
          closestInstance = targetSibling.closest('.xpanda'),
          ceiling = Math.ceil(targetIndex / APP.GO.updatedColumnCount) * APP.GO.updatedColumnCount,
          cloneDestination = closestInstance.find('.' + defaults.placeholder.class + '[data-until="' + ceiling + '"]'),
          cloneDestinationInner = cloneDestination.find('.' + defaults.placeholder.class + '-inner'),
          slideSpeed,
          indicatorDelay;

          // hide indicator
          APP.GO.hideIndicator();

          if (slide === true) {
            slideSpeed = defaults.placeholder.slideSpeed;
            indicatorDelay = 0;
          } else {
            slideSpeed = 0;
            indicatorDelay = 200;
          }

          // make all inner content invisible
          cloneDestinationInner.find('.x-info, .x-asset, .x-updated-content').animate({opacity: 0}, slideSpeed, 'linear').promise().then(function () {

            // update buttons
            APP.GO.updateButtons(targetIndex, ceiling);

            // add new content
            cloneDestinationInner.find('.x-asset, .x-info, .x-updated-content').remove();
            cloneDestinationInner.prepend('<div class="x-updated-content" style="opacity: 0;">' + content + '</div>').promise().then(function () {

              // reset placeholder inner
              cloneDestinationInner.css({'display': 'block'});

              // get height of child div
              var infoHeight = cloneDestinationInner.find('.x-updated-content').outerHeight();

              cloneDestination.animate({height: infoHeight + defaults.element.spaceBetweenRows}, slideSpeed, 'linear');
              cloneDestinationInner.animate({height: infoHeight}, slideSpeed, 'linear').promise().then(function () {
                cloneDestinationInner.find('.x-info, .x-asset, .x-updated-content').animate({opacity: 1}, slideSpeed, 'linear').promise().then(function () {

                  APP.GO.showIndicator(target, indicatorDelay);
                  APP.GO.styleActivePlaceholder();
                  APP.GO.lazyLoadAsset(targetIndex);

                });
              });

            });
          });

          // callbacks
          APP.GO.lazyLoadThumb();

        },

        // Show indicator.
        showIndicator: function (target, delay) {

          // variables
          var tPosition = target.position(),
          tWidth = target.width(),
          tLeft = tPosition.left + (tWidth  / 2),
          indicator = target.parent('.x-item-wrap').next('.' + defaults.placeholder.class).find('.x-indicator'),
          iWidth = indicator.width(),
          iHeight = indicator.height();

          indicator.css({
            'left': tLeft - (iWidth / 2),
            'top': defaults.element.spaceBetweenRows
          }).promise().then(function () {
            indicator.css({'opacity': 1}).promise().then(function () {
              setTimeout(function () {
                indicator.animate({'top': -(iHeight - defaults.element.spaceBetweenRows)}, 200);
              }, delay);
            });
          });

        },

        // Hide indicator.
        hideIndicator: function () {

          // variables
          var indicator = $('.x-indicator');

          indicator.css({
            'opacity': 0
          }).promise().then(function () {
            indicator.css({
              'left': 0,
              'top': 0
            });
          });

        },

        // Lazy load asset.
        lazyLoadAsset: function (index) {

          if (APP.GO.container.hasClass('x-lazyload-asset')) {

            // load placeholder image
            var clonePlaceHolder = $('.x-is-expanded'),
            placeholderImageWrap = clonePlaceHolder.find('.x-asset'),
            lowResImage = placeholderImageWrap.find('img'),
            highResImage = lowResImage.attr('data-src'),
            activeImageWrap = $(defaults.element.selector + '[data-index="' + index + '"]').find('.x-asset');

            if (lowResImage.attr('data-src') && lowResImage.attr('data-src') !== null) {

              // apply new source of high quality version image
              lowResImage.attr('src', highResImage);

              // check if image is done loading
              lowResImage.one('load', function () {

                if (!activeImageWrap.hasClass('x-was-loaded')) {
                  placeholderImageWrap.addClass('x-is-loaded');
                }

                // replace source of image
                var activeImage = activeImageWrap.find('img'),
                newActiveString = activeImage.attr('data-src');

                activeImage.attr('src', newActiveString).promise().then(function () {
                  activeImageWrap.addClass('x-was-loaded');
                });

              }).each(function () {
                if (this.complete) { $(this).trigger('load'); }
              });

            }

          }

        },

        // Lazy load thumbnail.
        lazyLoadThumb: function () {

          if (APP.GO.container.hasClass('x-lazyload-thumbnail')) {

            // get placeholder and define window bottom
            var placeholder = $('.' + defaults.placeholder.class),
            winBottom = APP.GO.winTop + APP.GO.winHeight;

            // for each placeholder
            placeholder.each(function () {

              // variables
              var $self = $(this),
              placeholderTop = $self.offset().top,
              placeholderBottom = placeholderTop - 100,
              dataUntil = $self.attr('data-until'),
              inViewThumb = $(defaults.element.selector + '[data-group="' + dataUntil + '"]');

              if (placeholderBottom <= winBottom && placeholderTop >= APP.GO.winTop) {

                // replace source of thumbnail image
                inViewThumb.each(function () {

                  var img = $(this).find('> a > img'),
                  newSource = img.attr('data-src');

                  img.attr('src', newSource).promise().then(function () {
                    inViewThumb.addClass('x-is-loaded');
                  });

                });

              }

            });

          }

        },

        // Create placeholder buttons.
        createButtons: function (updated) {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this),
            leftButton = $('<div class="x-arrow x-prev"></div>'),
            rightButton = $('<div class="x-arrow x-next"></div>'),
            closeButton = $('<div class="x-close"></div>');

            if (defaults.placeholder.showControls === true) {

              // create buttons
              if (updated === true) {
                thisInstance.find('.' + defaults.placeholder.class).find('.x-updated-content').append(leftButton).append(rightButton).append(closeButton);
              } else {
                thisInstance.find('.' + defaults.placeholder.class).find('.' + defaults.placeholder.class + '-inner').append(leftButton).append(rightButton).append(closeButton);
              }

            }

          });

        },

        // Update placeholder buttons.
        updateButtons: function (index, until) {

          APP.GO.container.each(function () {

            // variables
            var thisInstance = $(this);

            if (defaults.placeholder.showControls === true) {

              // add disabled classes if first or last child
              if (index === '1') {
                thisInstance.find('.' + defaults.placeholder.class + '[data-until="' + until + '"]').find('.x-arrow.x-prev').addClass('x-arrow-disabled');
              } else if (index === APP.GO.itemLength.toString()) {
                thisInstance.find('.' + defaults.placeholder.class + '[data-until="' + until + '"]').find('.x-arrow.x-next').addClass('x-arrow-disabled');
              } else {
                thisInstance.find('.' + defaults.placeholder.class).find('.x-arrow.x-prev, .x-arrow.x-next').removeClass('x-arrow-disabled');
              }

            }

          });

          APP.GO.onArrowClick();
          APP.GO.onKeyboardClick();

        },

        // Style active placeholder.
        styleActivePlaceholder: function () {

          APP.GO.container.each(function () {

            // Variables.
            var thisInstance = $(this),
            activeItem = thisInstance.find('.x-is-expanded'),
            horiMargins = (APP.GO.fixWidth) ? 0 : defaults.placeholder.marginSides;

            activeItem.css({
              'margin-right': horiMargins,
              'margin-left': horiMargins,
              'width': '100%'
            }).css('width', '-=' + (horiMargins * 2));

          });

        },

        // On arrows click.
        onArrowClick: function () {

          $('.x-arrow').off('click').one('click', function () {

            // variables
            var $self = $(this),
            activeItemIndex = $self.closest('.xpanda').find('.x-is-active').attr('data-index'),
            destination;

            // determine which way to navigate
            if ($self.hasClass('x-prev')) {
              destination = parseInt(activeItemIndex, 10) - 1;
            } else {
              destination = parseInt(activeItemIndex, 10) + 1;
            }

            // navigate
            $self.closest('.xpanda').find(defaults.element.selector + '[data-index="' + destination + '"]').trigger('click');

          });

        },

        // On close click.
        onCloseClick: function () {

          // on close button click
          $('.x-close').on('click', function () {

            $(this).closest('.xpanda').find('.x-is-active').trigger('click');

          });

        },

        // On keyboard click.
        onKeyboardClick: function () {

          // on keyboard keydown
          APP.GO.doc.off('keydown').one('keydown', function (e) {

            e.stopImmediatePropagation();

            // variables
            var keyboardActiveInstance = $('.x-keyboard-active'),
            currentActive = keyboardActiveInstance.find('.x-is-active'),
            index = currentActive.attr('data-index'),
            columnCount = parseInt(keyboardActiveInstance.find('.x-item-wrap').attr('data-columns'), 10),
            destination;

            if (currentActive.length > 0) {

              // escape
              if (e.which === 27) {
                // close xpanda
                currentActive.trigger('click');
              }
              // left
              if (e.which === 37) {
                destination = parseInt(index, 10) - 1;
                keyboardActiveInstance.find(defaults.element.selector + '[data-index="' + destination + '"]').trigger('click');
              }
              // up
              if (e.which === 38) {
                destination = parseInt(index, 10) - columnCount;
                keyboardActiveInstance.find(defaults.element.selector + '[data-index="' + destination + '"]').trigger('click');
              }
              // right
              if (e.which === 39) {
                destination = parseInt(index, 10) + 1;
                keyboardActiveInstance.find(defaults.element.selector + '[data-index="' + destination + '"]').trigger('click');
              }
              // down
              if (e.which === 40) {
                destination = parseInt(index, 10) + columnCount;
                keyboardActiveInstance.find(defaults.element.selector + '[data-index="' + destination + '"]').trigger('click');
              }

            }

          });

        },

        // History pushState.
        historyLoad: function () {

          // load based on browser path
          if (defaults.history) {

            var href = window.location.href,
            getHook = href.substring(href.lastIndexOf('xpnd='), href.length).slice(5),
            item = APP.GO.container.find(String(defaults.element.selector) + '[data-path="' + getHook + '"]');

            item.trigger('click');

          }

        }

      };

      // Trigger on document ready.
      APP.GO.globalVar();

      // Trigger only when everything else finished loading.
      APP.GO.win.on('load', function () {
        APP.GO.initialLoad();
        APP.GO.getColumns();
        APP.GO.createPlaceholders();
        APP.GO.styleItems();
        APP.GO.historyLoad();
      });

      // Trigger on window resize.
      APP.GO.win.on('resize', function () {
        APP.GO.throttleResizeFunc();
      });

      // Trigger on device orientation change.
      APP.GO.win.on('orientationchange', function () {
        // reload page with cache
        window.location.reload(false);
      });

      // Trigger on window scroll.
      APP.GO.win.on('scroll', function () {
        APP.GO.throttleScrollFunc();
      });

      // Trigger on history state change.
      APP.GO.win.on('popstate', function () {
        APP.GO.historyLoad();
      });

      // Trigger when clicked.
      APP.GO.onItemClick();
      APP.GO.onKeyboardClick();

    });

  };

}(jQuery));
