var endpointSearchWrapper = document.querySelector("#endpoint-search-input");
var endpointInputBox = endpointSearchWrapper.querySelector("input");
var endpointSuggBox = endpointSearchWrapper.querySelector(".autocom-box");
var endpoint_filter_icon = `<i class="fe-filter"></i>`;

var endpoint_col_suggestions = [
  'http_url',
  "http_status",
  "page_title",
  "gf_pattern",
  "content_type",
  "content_length",
  "technology",
  "webserver"
];

var endpoint_condition_suggestions = [
  "=",
  "!",
  ">",
  "<",
];

var endpoint_joiner = [
  "&",
  "|"
];

var endpoint_suggestion_selector = endpoint_col_suggestions;

endpointInputBox.onclick = (event) => {
  emptyArray = endpoint_suggestion_selector.filter((data)=>{
    return data.toLocaleLowerCase();
  });
  badge_color = "warning";
  emptyArray = emptyArray.map((data)=>{
    switch (data) {
      case "=":
      title = `Filters endpoint <span class="badge badge-soft-success">Equals</span> Some Value`;
      break;
      case "!":
      title = `Filters endpoint <span class="badge badge-soft-danger">Not Equals</span> Some Value`;
      break;
      case ">":
      title = `Filters endpoint <span class="badge badge-soft-dark">Greater than</span> Some Value`;
      break;
      case "<":
      title = `Filters endpoint <span class="badge badge-soft-dark">Less than</span> Some Value`;
      break;
      case "&":
      title = `<span class="badge badge-soft-danger">& and</span> Match endpoint if <span class="badge badge-soft-danger">all args</span> are true`;
      break;
      case "|":
      title = `<span class="badge badge-soft-warning">| or</span> Match endpoint if <span class="badge badge-soft-warning">either of one</span> is true`;
      break;
      default:
      badge_color = "info";
      title = `Filter endpoint that contains <span class="badge badge-soft-blue">${data}</span>`;
    }
    return data = `<li id="dropdown-li" class="text-dark"><div class="row"><div class="col-6" id="filter_name"><span class="text-${badge_color}">${endpoint_filter_icon}</span>&nbsp;${data}</div><div class="col-6 text-dark" id="filter_name"> ${title}</span></div></div></li>`;
  });

  endpointSearchWrapper.classList.add("active");
  endpoint_showSuggestions(emptyArray);
  let allList = endpointSuggBox.querySelectorAll("li");
  for (let i = 0; i < allList.length; i++) {
    allList[i].setAttribute("onclick", "endpoint_select(this)");
  }
}

function endpoint_showSuggestions(list){
  let listData;
  listData = list.join('');
  endpointSuggBox.innerHTML = listData;
}

function endpoint_select(element){
  let selectData = element.textContent.split(" ")[0];
  endpointInputBox.value = $('#endpoints-search').val() + selectData;
  $("#endpoints-search").focus();
}

endpoint_col_suggestions_used = true;

$('#endpoints-search').on("change paste keyup", function(event) {
  user_input = $(this).val();
  if (event.which == 13 || event.which == 27) {
    endpointSearchWrapper.classList.remove("active");
    $('#endpoint-search-button').click();
    return;
  }

  if (user_input.length == 0) {
    endpoint_suggestion_selector = endpoint_col_suggestions;
    $('#endpoint-search-button').click();
    endpoint_col_suggestions_used = true;
  }

  cond_split_val = $(this).val().split(new RegExp('[=><!&|]', 'g'));

  last_obj = cond_split_val.slice(-1)[0];

  if (endpoint_col_suggestions.indexOf(last_obj) > -1) {
    endpoint_suggestion_selector = endpoint_condition_suggestions;
    endpoint_col_suggestions_used = false;
  }

  else if (["=", "!", ">", "<"].indexOf($(this).val().slice(-1)) > -1) {
    endpoint_suggestion_selector = endpoint_joiner;
    endpoint_col_suggestions_used = false;
  }


  else if (["&", "|"].indexOf($(this).val().slice(-1)) > -1) {
    endpoint_suggestion_selector = endpoint_col_suggestions;
    endpoint_col_suggestions_used = true;
  }

  if (endpoint_col_suggestions_used) {
    endpoint_suggestion_selector = endpoint_col_suggestions.filter((data)=>{
      return data.toLocaleLowerCase().includes(last_obj.toLocaleLowerCase());
    });
  }

  document.getElementById("endpoints-search").click();
});

$(document).on('click', function (e) {
  // console.log($(e.target).attr('id'));
  if ($(e.target).attr('id') != 'endpoints-search' && $(e.target).attr('id') != 'filter_name') {
    endpointSearchWrapper.classList.remove("active");
  }
});
