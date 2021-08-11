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
