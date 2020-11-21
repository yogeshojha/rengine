// seperate hostname and url
// Referenced from https://stackoverflow.com/questions/736513/how-do-i-parse-a-url-into-hostname-and-path-in-javascript
function getParsedURL(url) {
    var parser = new URL(url);
    return parser.pathname+parser.search;
};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Source: https://portswigger.net/web-security/cross-site-scripting/preventing#encode-data-on-output
function htmlEncode(str){
  return String(str).replace(/[^\w. ]/gi, function(c){
     return '&#'+c.charCodeAt(0)+';';
  });
}

function deleteScheduledScan(id, task_name)
{
    const delAPI = "../delete/scheduled_task/"+id;
    swal.queue([{
        title: 'Are you sure you want to delete ' + task_name + '?',
        text: "You won't be able to revert this!",
        type: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Delete',
        padding: '2em',
        showLoaderOnConfirm: true,
        preConfirm: function() {
          return fetch(delAPI, {
	            method: 'POST',
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            })
            .then(function (response) {
                return response.json();
            })
            .then(function(data) {
                // TODO Look for better way
               return location.reload();
            })
            .catch(function() {
              swal.insertQueueStep({
                type: 'error',
                title: 'Oops! Unable to delete the scheduled task!'
              })
            })
        }
    }])
}

function change_scheduled_task_status(id)
{
    const taskStatusApi = "../toggle/scheduled_task/"+id;

    return fetch(taskStatusApi, {
        method: 'POST',
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": getCookie("csrftoken")
        }
    })
}

function change_vuln_status(id)
{
    const vulnStatusApi = "../toggle/vuln_status/"+id;

    return fetch(vulnStatusApi, {
        method: 'POST',
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": getCookie("csrftoken")
        }
    })
}
