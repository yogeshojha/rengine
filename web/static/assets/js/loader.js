// from:https://github.com/jserz/js_piece/blob/master/DOM/ChildNode/remove()/remove().md
(function (arr) {
    arr.forEach(function (item) {
      if (item.hasOwnProperty('remove')) {
        return;
      }
      Object.defineProperty(item, 'remove', {
        configurable: true,
        enumerable: true,
        writable: true,
        value: function remove() {
          this.parentNode.removeChild(this);
        }
      });
    });
})([Element.prototype, CharacterData.prototype, DocumentType.prototype]);


function changeTheme(){
   const theme_switch = document.getElementById("theme-switch");
   if (theme_switch.checked) {
    DarkReader.setFetchMethod(window.fetch);
    DarkReader.enable();
     // Add the ff. line to write to memory.
     localStorage.setItem("my-theme","dark");
   }
   else {
     DarkReader.disable();
     // Add the ff. line to write to memory.
     localStorage.setItem("my-theme",null);
   }
 }
