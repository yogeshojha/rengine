// all the js code for the bountyhub page

document.addEventListener('DOMContentLoaded', function() {
    let allPrograms = [];
    const container = document.getElementById('program_cards');
    const importBtn = document.getElementById('importProgramsBtn');
    const clearBtn = document.getElementById('clearSelectionsLink');
    const filterSelect = document.querySelector('select[aria-label="Program type"]');
    const searchInput = document.querySelector('#search-program-box');
    const showClosedCheckbox = document.getElementById('show-closed-programs');
    const sortSelect = document.getElementById('sort-select');
    const showBookmarkedCheckbox = document.getElementById('show-bookmarked-programs');

    // Debounce function for search input to avoid making too many requests
    const debounce = (func, delay) => {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(null, args), delay);
        };
    };

    async function fetchPrograms(isSortingRequest = false, isBookmarkedRequest = false) {
        if (isSortingRequest) {
            showLoadingIndicator("Sorting...");
        } else if (isBookmarkedRequest) {
            showLoadingIndicator("Loading Bookmarked Programs");
        } else {
            showLoadingIndicator("Loading HackerOne Programs");
        }

        let api_url = isBookmarkedRequest ? '/api/hackerone-programs/bookmarked_programs/' : '/api/hackerone-programs/';

        const sortParams = updateSortingParams();
        const queryParams = new URLSearchParams(sortParams).toString();

        if (queryParams) {
            api_url += '?' + queryParams;
        }

        try {
            const response = await fetch(api_url, {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            allPrograms = data;
            displayPrograms(data);
        } catch (error) {
            displayErrorMessage("An error occurred while fetching the hackerone programs. Please try again later. Make sure you have hackerone api key set in your API Vault.");
            console.error('Error:', error);
        } finally {
            hideLoadingIndicator();
        }
    }

    function displayPrograms(programs) {
        container.innerHTML = ''; // clear up the html content

        if (!programs || programs.length === 0) {
            displayErrorMessage("No programs available at the moment.");
            return;
        }

        const fragment = document.createDocumentFragment();
        const template = document.createElement('template');

        programs.forEach((program) => {
            const { attributes } = program;
            template.innerHTML = `
                <div class="col-md-6 col-lg-4 col-xl-3 mb-3 program-card-wrapper" style="opacity: 0; transform: translateY(20px); transition: opacity 0.3s ease, transform 0.3s ease;">
                    <div class="card h-100 shadow-sm position-relative overflow-hidden bbp-card card-selectable" data-offers-bounties="${attributes.offers_bounties}" data-program-state="${attributes.state}">
                        <div class="card-body py-2 px-3">
                            <!-- Card content -->
                        </div>
                    </div>
                </div>
            `;
            const cardNode = template.content.firstElementChild.cloneNode(true);
            cardNode.querySelector('.card-body').innerHTML = generateCardContent(attributes);
            fragment.appendChild(cardNode);
        });

        container.appendChild(fragment);
        animateCards();
        initializeFilter();
    }

    function animateCards() {
        const cards = container.querySelectorAll('.program-card-wrapper');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 50); // staggering anims for sort, search and filter and even first load
        });
    }

    function generateCardContent(attributes) {
        return `
            <div class="d-flex align-items-center mb-2">
                <img src="${attributes.profile_picture}" alt="${attributes.name}" class="rounded-circle me-3" width="40" height="40" loading="lazy">
                <div>
                    <h5 class="card-title mb-0">${attributes.name}${attributes.bookmarked ? '<i class="text-warning mdi mdi-bookmark-check" title="Bookmarked Program"></i>' : ''}</h5>
                    <small class="text-muted"><a href="https://hackerone.com/${attributes.handle}" class="handle-link" target="_blank">@${attributes.handle}</a></small>
                </div>
            </div>
            <div class="mb-2">
                <span class="badge ${attributes.submission_state === 'open' ? 'bg-success' : 'bg-danger'} bg-opacity-10 text-${attributes.submission_state === 'open' ? 'success' : 'danger'} me-1 mb-1">${attributes.submission_state === 'open' ? 'Open' : 'Closed'}</span>
                <span class="badge bg-primary bg-opacity-10 text-primary me-1 mb-1">${attributes.state === 'public_mode' ? 'Public' : 'Private'}</span>
                ${attributes.offers_bounties ? '<span class="badge bg-info bg-opacity-10 text-info me-1 mb-1">Bounty</span>' : '<span class="badge bg-danger bg-opacity-10 text-danger me-1 mb-1">VDP</span>'}
                ${attributes.open_scope ? '<span class="badge bg-warning bg-opacity-10 text-warning mb-1">Open Scope</span>' : ''}
                ${isProgramNew(attributes.started_accepting_at) ? '<span class="badge bg-primary bg-opacity-10 text-primary mb-1"><i class="fe-zap"></i> New</span>' : ''}
            </div>
            <div class="d-flex justify-content-between mb-2 small">
                <div><i class="bi bi-flag me-1"></i> Reports: ${attributes.number_of_reports_for_user}</div>
                <div><i class="bi bi-currency-dollar me-1"></i> Earnings: $${attributes.bounty_earned_for_user.toFixed(2)}</div>
            </div>
            <hr class="my-2">
            <div class="d-flex justify-content-between text-muted small mb-2">
                <div><i class="bi bi-calendar me-1"></i> Since ${new Date(attributes.started_accepting_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</div>
                <div><i class="bi bi-globe me-1"></i> ${attributes.currency.toUpperCase()}</div>
            </div>
            <button class="btn btn-outline-primary btn-sm w-100 mt-2 btn-see-details" onclick="see_detail('${attributes.handle}')">See details</button>
        `;
    }

    function initializeFilter() {
        const filterAndSearchCards = debounce(() => {
            const selectedFilter = filterSelect.value;
            const searchTerm = searchInput.value.toLowerCase().trim();
            const showClosed = showClosedCheckbox.checked;

            const visibleCards = Array.from(container.querySelectorAll('.program-card-wrapper')).filter(cardWrapper => {
                const card = cardWrapper.querySelector('.bbp-card');
                const name = card.querySelector('h5').textContent.toLowerCase();
                const offersBounties = card.dataset.offersBounties === 'true';
                const isPrivate = card.dataset.programState === 'private_mode';
                const isClosed = card.querySelector('.badge').textContent.trim() !== 'Open';

                let shouldShow = true;

                switch(selectedFilter) {
                    case 'Bounty Eligible':
                        shouldShow = offersBounties;
                        break;
                    case 'VDP':
                        shouldShow = !offersBounties;
                        break;
                    case 'Private Programs':
                        shouldShow = isPrivate;
                        break;
                }

                shouldShow = shouldShow && (!searchTerm || name.includes(searchTerm));
                shouldShow = shouldShow && (showClosed || !isClosed);

                return shouldShow;
            });

            container.querySelectorAll('.program-card-wrapper').forEach(card => card.style.display = 'none');
            visibleCards.forEach(card => card.style.display = '');
        }, 100);

        filterSelect.addEventListener('change', filterAndSearchCards);
        searchInput.addEventListener('input', filterAndSearchCards);
        showClosedCheckbox.addEventListener('change', filterAndSearchCards);
        showBookmarkedCheckbox.addEventListener('change', async (event) => {
            if (event.target.checked) {
                await fetchPrograms(false, true);
            } else {
                await fetchPrograms(false, false);
            }
            filterAndSearchCards();
        });
        
        filterAndSearchCards();
    }

    function createCardData(cardWrapper) {
        const card = cardWrapper.querySelector('.bbp-card');
        return {
            wrapper: cardWrapper,
            name: card.querySelector('h5').textContent.toLowerCase(),
            offersBounties: card.dataset.offersBounties === 'true',
            isPrivate: card.dataset.programState === 'private_mode',
            isClosed: card.querySelector('.badge').textContent.trim() !== 'Open'
        };
    }

    function updateSortingParams() {
        const [sortBy, sortOrder] = sortSelect.value.split('-');
        const apiSortBy = {
            name: 'name',
            reports: 'reports',
            posted: 'age'
        }[sortBy] || 'age';
        
        return { sort_by: apiSortBy, sort_order: sortOrder || 'desc' };
    }

    // Event listeners
    sortSelect.addEventListener('change', () => fetchPrograms(true, false));
    container.addEventListener('click', handleCardClick);
    clearBtn.addEventListener('click', clearAllSelections);

    function handleCardClick(event) {
        const card = event.target.closest('.card-selectable');
        if (card) {
            if (event.target.closest('.btn-see-details') || event.target.closest('.handle-link')) {
                // Handle "See details" button or handle link click
                return;
            }
            toggleCardSelection(card);
        }
    }

    function toggleCardSelection(card) {
        card.classList.toggle('card-selected');
        updateImportButton();
    }

    function updateImportButton() {
        const selectedCards = container.querySelectorAll('.card-selected');
        const count = selectedCards.length;
        
        importBtn.disabled = count === 0;
        importBtn.innerHTML = count === 0 ? '<i class="fe-download-cloud"></i> Import Programs' : `<i class="fe-download-cloud"></i> Import ${count} Program${count !== 1 ? 's' : ''}`;
        clearBtn.style.display = count === 0 ? 'none' : 'inline';
    }

    function clearAllSelections() {
        container.querySelectorAll('.card-selected').forEach(card => card.classList.remove('card-selected'));
        updateImportButton();
    }

    function showLoadingIndicator(message) {
        Swal.fire({
            title: message,
            text: "Please wait",
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            willOpen: () => {
                Swal.showLoading();
            }
        });
    }

    function hideLoadingIndicator() {
        Swal.close();
    }

    fetchPrograms(false, false);
});

function isProgramNew(startedAcceptingAt) {
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
    return new Date(startedAcceptingAt) > threeMonthsAgo;
}

// see detail function call
function see_detail(handle) {
    Swal.fire({
        title: 'Loading...',
        html: 'Fetching program details',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        willOpen: () => {
            Swal.showLoading();
        }
    });

    fetch(`/api/hackerone-programs/${handle}/program_details/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            Swal.close();

            populateModal(data);
        })
        .catch(error => {
            console.error('Error:', error);
            
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: 'There was an error fetching the program details. Please try again.',
            });
        });
}


function populateModal(data) {
    const attributes = data.attributes;

    const modalHTML = `
    <div class="modal fade" id="programDetailModal" tabindex="-1" aria-labelledby="programDetailModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="programDetailModalLabel">
                        <img src="${attributes.profile_picture}" alt="${attributes.name}" class="program-profile-picture me-3">
                        <span class="program-name">${attributes.name}</span>
                        ${attributes.bookmarked ? '<i class="fas fa-bookmark text-muted ms-2" title="Bookmarked Program"></i>' : ''}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <div id="badgeContainer" class="mb-3"></div>
                            <p class="text-muted">
                                <i class="fas fa-user me-2"></i>
                                <a href="https://hackerone.com/${attributes.handle}" class="handle-link" target="_blank">@${attributes.handle}</a>
                            </p>
                            <p class="text-muted">
                                <i class="fas fa-calendar-alt me-2"></i>
                                Program active since ${new Date(attributes.started_accepting_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                            </p>
                        </div>
                        <div class="col-md-4">
                            <div class="program-stat-card mb-3">
                                <h6 class="text-muted">Reports</h6>
                                <h3>${attributes.number_of_reports_for_user || '0'}</h3>
                            </div>
                            <div class="program-stat-card">
                                <h6 class="text-muted">Earnings</h6>
                                <h3>$${(attributes.bounty_earned_for_user || 0).toFixed(2)} ${attributes.currency.toUpperCase()}</h3>
                            </div>
                        </div>
                    </div>

                    <h5 class="section-title mb-3">Assets on Scope</h5>
                    <div class="accordion custom-program-accordion" id="assetAccordion"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
                    <a href="https://hackerone.com/${attributes.handle}" target="_blank" class="btn btn-primary">See full details</a>
                </div>
            </div>
        </div>
    </div>
    `;

    // Remove any existing modal
    const existingModal = document.getElementById('programDetailModal');
    if (existingModal) {
        existingModal.remove();
    }

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    populateBadges(attributes);

    populateAssetAccordion(data);

    const modal = new bootstrap.Modal(document.getElementById('programDetailModal'));
    modal.show();
}
function populateBadges(attributes) {
    const badgeContainer = document.getElementById('badgeContainer');
    const badges = [
        {
            condition: true,
            classes: `${attributes.submission_state === 'open' ? 'bg-success' : 'bg-danger'} text-white`,
            text: attributes.submission_state === 'open' ? 'Open' : 'Closed'
        },
        {
            condition: true,
            classes: 'bg-primary text-white',
            text: attributes.state === 'public_mode' ? 'Public' : 'Private'
        },
        {
            condition: true,
            classes: attributes.offers_bounties ? 'badge bg-info bg-opacity-10 text-info' : 'badge bg-danger bg-opacity-10 text-danger',
            text: attributes.offers_bounties ? 'Bounty' : 'VDP'
        },
        {
            condition: attributes.open_scope,
            classes: 'bg-success text-white',
            text: 'Open Scope'
        },
        {
            condition: isProgramNew(attributes.started_accepting_at),
            classes: 'bg-primary text-white',
            text: 'New',
            icon: 'fe-zap'
        }
    ];

    badges.forEach(badge => {
        if (badge.condition) {
            badgeContainer.innerHTML += `
                <span class="badge ${badge.classes}">
                    ${badge.icon ? `<i class="${badge.icon} me-1"></i>` : ''}${badge.text}
                </span>
            `;
        }
    });
}

function populateAssetAccordion(data) {
    const accordion = document.getElementById('assetAccordion');
    const assetTypes = {
        WILDCARD: [], DOMAIN: [], IP_ADDRESS: [], CIDR: [], URL: []
    };

    data.relationships.structured_scopes.data.forEach(scope => {
        const type = scope.attributes.asset_type;
        if (assetTypes.hasOwnProperty(type)) {
            assetTypes[type].push(scope.attributes.asset_identifier);
        }
    });

    Object.entries(assetTypes).forEach(([type, assets], index) => {
        if (assets.length > 0) {
            const item = createAccordionItem(type, assets, index);
            accordion.appendChild(item);
        }
    });
}

function createAccordionItem(type, assets, index) {
    const item = document.createElement('div');
    item.className = 'accordion-item border-0 mb-2';
    item.innerHTML = `
        <h2 class="accordion-header" id="heading${type}">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                    data-bs-target="#collapse${type}" aria-expanded="">
                ${type}s (${assets.length})
            </button>
        </h2>
        <div id="collapse${type}" class="accordion-collapse collapse" 
             aria-labelledby="heading${type}" data-bs-parent="#assetAccordion">
            <div class="accordion-body">
                <ul>
                    ${assets.map(asset => `<li>${asset}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
    return item;
}