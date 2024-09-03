// this js file will be used to do everything js related to the bountyhub page

document.addEventListener('DOMContentLoaded', function() {
    const api_url = '/api/hackerone-programs/';

    Swal.fire({
        title: "Loading HackerOne Programs",
        text: "Fetching the latest data...",
        icon: "info",
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch(api_url, {
        method: "GET",
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        Swal.close();

        displayPrograms(data);
    })
    .catch(error => {
        Swal.close();
        displayErrorMessage("An error occurred while fetching the data. Please try again later. Make sure you have hackerone api key set in your API Vault.");
        console.error('Error:', error);
    });

    function displayPrograms(programs) {
        const container = document.getElementById('program_cards');
        container.innerHTML = '';
    
        if (!programs || programs.length === 0) {
            displayErrorMessage("No programs available at the moment.");
            return;
        }
    
        programs.forEach(program => {
            const { id, attributes } = program;
            const card = document.createElement('div');
            card.className = 'col-md-6 col-lg-4 col-xl-3 mb-3 program-card-wrapper';
            card.innerHTML = `
            <div class="card h-100 shadow-sm position-relative overflow-hidden bbp-card card-selectable" data-offers-bounties="${attributes.offers_bounties}" data-program-state="${attributes.state}">

                <div class="card-body py-2 px-3">
                <div class="d-flex align-items-center mb-2">
                    <img src="${attributes.profile_picture}" alt="${attributes.name}" class="rounded-circle me-3" width="40" height="40" loading="lazy">
                    <div>
                    <h5 class="card-title mb-0">${attributes.name}&nbsp;
                        ${attributes.bookmarked ? '<i class="text-warning mdi mdi-bookmark-check" data-bs-toggle="tooltip" data-bs-placement="top" title="Bookmarked Program"></i>' : ''}
                    </h5>
                    <small class="text-muted">@${attributes.handle}</small>
                    </div>
                </div>

                <div class="mb-2">
                    <span class="badge ${attributes.submission_state === 'open' ? 'bg-success' : 'bg-danger'} bg-opacity-10 text-${attributes.submission_state === 'open' ? 'success' : 'danger'} me-1 mb-1">${attributes.submission_state === 'open' ? 'Open for Submission' : 'Closed'}</span>
                    <span class="badge bg-primary bg-opacity-10 text-primary me-1 mb-1">${attributes.state === 'public_mode' ? 'Public Program' : 'Private Program'}</span>
                    ${attributes.offers_bounties ? '<span class="badge bg-info bg-opacity-10 text-info me-1 mb-1">Bounty $$$</span>' : ''}
                    ${attributes.open_scope ? '<span class="badge bg-warning bg-opacity-10 text-warning mb-1">Open Scope</span>' : ''}
                </div>

                <div class="d-flex justify-content-between mb-2 small">
                    <div><i class="bi bi-flag me-1"></i> My Reports: ${attributes.number_of_reports_for_user}</div>
                    <div><i class="bi bi-currency-dollar me-1"></i> My Earnings: $${attributes.bounty_earned_for_user.toFixed(2)}</div>
                </div>

                <hr class="my-2">

                <div class="d-flex justify-content-between text-muted small mb-2">
                    <div><i class="bi bi-calendar me-1"></i> Since ${new Date(attributes.started_accepting_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</div>
                    <div><i class="bi bi-globe me-1"></i> ${attributes.currency.toUpperCase()}</div>
                </div>
                <a href="#" class="btn btn-outline-primary btn-sm w-100 mt-2" id="btn-see-details">See details</a>
                </div>
            </div>
            `;


            // Initialize tooltips esp for bookmarked programs
            const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach((tooltip) => {
                new bootstrap.Tooltip(tooltip);
            });
            container.appendChild(card);

            initializeFilter();

        });
    }

    function displayErrorMessage(message) {
        const container = document.getElementById('program_cards');
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger" role="alert">
                    <i class="fe-alert-triangle me-2"></i>
                    ${message}
                </div>
            </div>
        `;
    }

    // below has everything to do with card selection and import button
    const container = document.getElementById('program_cards');
    const importBtn = document.getElementById('importProgramsBtn');
    const clearBtn = document.getElementById('clearSelectionsLink');

    container.addEventListener('click', function(event) {
        const card = event.target.closest('.card-selectable');
        if (card) {
            toggleCardSelection(event, card);
        }
    });

    function toggleCardSelection(event, card) {
        if (event.target.closest('#btn-see-details')) {
            // If it's the "See details" button, don't toggle selection, maybe we need other actions in the future here
            return;
        }

        card.classList.toggle('card-selected');
        updateImportButton();
    }

    function updateImportButton() {
        const selectedCards = container.querySelectorAll('.card-selected');
        const count = selectedCards.length;
        
        if (count === 0) {
            importBtn.disabled = true;
            importBtn.innerHTML = '<i class="fe-download-cloud"></i> Import Programs';
            clearBtn.style.display = 'none';
        } else {
            importBtn.disabled = false;
            importBtn.innerHTML = `<i class="fe-download-cloud"></i> Import ${count} Program${count !== 1 ? 's' : ''}`;
            clearBtn.style.display = 'inline';
        }
    }

    function clearAllSelections() {
        const selectedCards = container.querySelectorAll('.card-selected');
        selectedCards.forEach(card => card.classList.remove('card-selected'));
        updateImportButton();
    }

    // clear btn listener
    clearBtn.addEventListener('click', function(event) {
        event.preventDefault();
        clearAllSelections();
    });


    // init state
    updateImportButton();


    // we begin filtering here
    function initializeFilter() {
        const filterSelect = document.querySelector('select[aria-label="Program type"]');
        const container = document.getElementById('program_cards');
        const allCards = Array.from(container.querySelectorAll('.program-card-wrapper'));
        const searchInput = document.querySelector('#search-program-box');
    
        // Pre-compute card data to avoid querying the DOM on each filter/search
        const cardData = allCards.map(cardWrapper => {
            const card = cardWrapper.querySelector('.bbp-card');
            return {
                wrapper: cardWrapper,
                name: card.querySelector('h5').textContent.toLowerCase(),
                offersBounties: card.dataset.offersBounties === 'true',
                isPrivate: card.dataset.programState === 'private_mode'
            };
        });
    
        let lastFilter = '';
        let lastSearch = '';
    
        function filterAndSearchCards() {
            const selectedFilter = filterSelect.value;
            const searchTerm = searchInput.value.toLowerCase().trim();
    
            if (selectedFilter === lastFilter && searchTerm === lastSearch) return;
            lastFilter = selectedFilter;
            lastSearch = searchTerm;
    
            const visibleCards = cardData.filter(({ offersBounties, isPrivate, name }) => {
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
    
                return shouldShow && (!searchTerm || name.includes(searchTerm));
            });
    
            // Batch DOM updates to avoid reflows and make the transition smoother
            requestAnimationFrame(() => {
                cardData.forEach(({ wrapper }) => {
                    wrapper.style.display = 'none';
                    wrapper.classList.add('filtering-hide');
                });
    
                visibleCards.forEach(({ wrapper }) => {
                    wrapper.style.display = '';
                    wrapper.classList.remove('filtering-hide');
                });
            });
        }
    
        filterSelect.addEventListener('change', filterAndSearchCards);
        searchInput.addEventListener('input', filterAndSearchCards);
        
        filterAndSearchCards(); // init call
    }
});