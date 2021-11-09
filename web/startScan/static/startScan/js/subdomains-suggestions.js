var searchWrapper = document.querySelector(".search-input");
var inputBox = searchWrapper.querySelector("input");
var suggBox = searchWrapper.querySelector(".autocom-box");
var filter_icon = `<i class="fe-filter"></i>`;

var col_suggestions = [
  "name",
  "page_title",
  "http_status",
  "is_important",
  "cname",
  "http_url",
  "technology",
  "port",
  "webserver",
  "content_type",
  "ip_address",
  "content_length",
];

var condition_suggestions = [
  "=",
  "!",
  ">",
  "<",
];

var joiner = [
  "&",
  "|"
];

var suggestion_selector = col_suggestions;

inputBox.onclick = (event) => {
  emptyArray = suggestion_selector.filter((data)=>{
    return data.toLocaleLowerCase();
  });
  badge_color = "warning";
  emptyArray = emptyArray.map((data)=>{
    switch (data) {
      case "=":
      title = `Filters Subdomain <span class="badge badge-soft-success">Equals</span> Some Value`;
      break;
      case "!":
      title = `Filters Subdomain <span class="badge badge-soft-danger">Not Equals</span> Some Value`;
      break;
      case ">":
      title = `Filters Subdomain <span class="badge badge-soft-blue">Greater than</span> Some Value`;
      break;
      case "<":
      title = `Filters Subdomain <span class="badge badge-soft-blue">Less than</span> Some Value`;
      break;
      case "&":
      title = `<span class="badge badge-soft-danger">& and</span> Match Subdomain if <span class="badge badge-soft-danger">all args</span> are true`;
      break;
      case "|":
      title = `<span class="badge badge-soft-warning">| or</span> Match Subdomain if <span class="badge badge-soft-warning">either of one</span> is true`;
      break;
      default:
      badge_color = "primary";
      title = `Filter subdomain that contains <span class="badge badge-soft-blue">${data}</span>`;
    }
    return data = `<li id="dropdown-li" class="text-dark"><div class="row"><div class="col-6" id="filter_name"><span class="text-${badge_color}">${filter_icon}</span>&nbsp;${data}</div><div class="col-6 text-dark" id="filter_name"> ${title}</span></div></div></li>`;
  });

  searchWrapper.classList.add("active");
  showSuggestions(emptyArray);
  let allList = suggBox.querySelectorAll("li");
  for (let i = 0; i < allList.length; i++) {
    allList[i].setAttribute("onclick", "select(this)");
  }
}

function showSuggestions(list){
  let listData;
  listData = list.join('');
  suggBox.innerHTML = listData;
}

function select(element){
  let selectData = element.textContent.split(" ")[0];
  inputBox.value = $('#subdomains-search').val() + selectData;
  $("#subdomains-search").focus();

}


col_suggestions_used = true;

$('#subdomains-search').on("change paste keyup", function(event) {
  user_input = $(this).val();
  if (event.which == 13 || event.which == 27) {
    searchWrapper.classList.remove("active");
    $('#subdomain-search-button').click();
    return;
  }
  if (user_input.length == 0) {
    suggestion_selector = col_suggestions;
    $('#subdomain-search-button').click();
    col_suggestions_used = true;
  }
  cond_split_val = $(this).val().split(new RegExp('[=><!&|]', 'g'));

  last_obj = cond_split_val.slice(-1)[0];

  if (col_suggestions.indexOf(last_obj) > -1) {
    suggestion_selector = condition_suggestions;
    col_suggestions_used = false;
  }

  else if (["=", "!", ">", "<"].indexOf($(this).val().slice(-1)) > -1) {
    suggestion_selector = joiner;
    col_suggestions_used = false;
  }


  else if (["&", "|"].indexOf($(this).val().slice(-1)) > -1) {
    suggestion_selector = col_suggestions;
    col_suggestions_used = true;
  }

  if (col_suggestions_used) {
    suggestion_selector = col_suggestions.filter((data)=>{
      return data.toLocaleLowerCase().includes(last_obj.toLocaleLowerCase());
    });
  }

  document.getElementById("subdomains-search").click();
});

$(document).on('click', function (e) {
  // console.log($(e.target).attr('id'));
  if ($(e.target).attr('id') != 'subdomains-search' && $(e.target).attr('id') != 'filter_name') {
     searchWrapper.classList.remove("active");
   }
});
