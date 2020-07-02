// https://stackoverflow.com/a/11384018
function openInNewTab(href) {
  window.open(href, '_blank');
  window.focus();
}

// seperate hostname and url
// Referenced from https://stackoverflow.com/questions/736513/how-do-i-parse-a-url-into-hostname-and-path-in-javascript
function getParsedURL(url) {
    var parser = new URL(url);
    return parser.pathname+parser.search;
};
