/*jslint  browser: true, white: true, plusplus: true */
/*global $, countries */

$(function () {
    'use strict';

    var countriesArray = $.map(countries, function (value, key) { return { value: value, data: key }; });

    // Setup jQuery ajax mock:
    $.mockjax({
        url: '*',
        responseTime: 2000,
        response: function (settings) {
            var query = settings.data.query,
                queryLowerCase = query.toLowerCase(),
                re = new RegExp('\\b' + $.Autocomplete.utils.escapeRegExChars(queryLowerCase), 'gi'),
                suggestions = $.grep(countriesArray, function (country) {
                     // return country.value.toLowerCase().indexOf(queryLowerCase) === 0;
                    return re.test(country.value);
                }),
                response = {
                    query: query,
                    suggestions: suggestions
                };

            this.responseText = JSON.stringify(response);
        }
    });

    var nhlTeams = ['Atlanta', 'Boston', 'Buffalo', 'Calgary', 'Carolina', 'Chicago', 'Colorado', 'Columbus', 'Dallas', 'Detroit', 'Edmonton', 'Florida', 'Los Angeles', 'Minnesota', 'Montreal', 'Nashville', ];
    var nbaTeams = ['New Jersey', 'New Rork', 'New York', 'Ottawa', 'Philadelphia', 'Phoenix', 'Pittsburgh', 'Saint Louis', 'San Jose', 'Tampa Bay', 'Toronto Maple', 'Vancouver', 'Washington'];
    var nhl = $.map(nhlTeams, function (team) { return { value: team, data: { category: 'Section A' }}; });
    var nba = $.map(nbaTeams, function (team) { return { value: team, data: { category: 'Section B' } }; });
    var teams = nhl.concat(nba);

    // Initialize autocomplete with local lookup:
    $('#city').autocomplete({
        lookup: teams,
        minChars: 1,
        onSelect: function (suggestion) {
            $('#selection').html('You selected: ' + suggestion.value);
        },
        showNoSuggestionNotice: true,
        noSuggestionNotice: 'Sorry, no matching results',
        groupBy: 'category'
    });

    $('#country').autocomplete({
        lookup: countriesArray,
        minChars: 1,
        onSelect: function (suggestion) {
            $('#selection-country').html('You selected: ' + suggestion.value);
        },
        showNoSuggestionNotice: true,
        noSuggestionNotice: 'Sorry, no matching results',
        groupBy: 'category'
    });

    
    // Initialize autocomplete with custom appendTo:
    $('#autocomplete-custom-append').autocomplete({
        lookup: countriesArray,
        appendTo: '#suggestions-container'
    });

    // Initialize autocomplete with custom appendTo:
    $('#autocomplete-dynamic').autocomplete({
        lookup: countriesArray
    });
});