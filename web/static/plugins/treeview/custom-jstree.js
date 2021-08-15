
// Custom 1

var toggler = document.getElementsByClassName("caret");
var i;

for (i = 0; i < toggler.length; i++) {
  toggler[i].addEventListener("click", function() {
    this.parentElement.querySelector(".nested").classList.toggle("active");
    this.classList.toggle("caret-down");
  });
}

// Custom 2

var folder = $('.file-tree li.file-tree-folder'),
    file = $('.file-tree li');

folder.on("click", function(a) {
  $(this).children('ul').slideToggle(400, function() {
      $(this).parent("li").toggleClass("open")
  }), a.stopPropagation()
})

file.on('click', function(b){
    b.stopPropagation();
})