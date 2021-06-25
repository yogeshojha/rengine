/*!
 * Snackbar v0.1.9
 * http://polonel.com/Snackbar
 *
 * Copyright 2017 Chris Brame and other contributors
 * Released under the MIT license
 * https://github.com/polonel/Snackbar/blob/master/LICENSE
 */
!function(a,b){"use strict";"function"==typeof define&&define.amd?define([],function(){return a.Snackbar=b()}):"object"==typeof module&&module.exports?module.exports=a.Snackbar=b():a.Snackbar=b()}(this,function(){var a={};a.current=null;var b={text:"Default Text",textColor:"#FFFFFF",width:"auto",showAction:!0,actionText:"Dismiss",actionTextColor:"#25d5e4",showSecondButton:!1,secondButtonText:"",secondButtonTextColor:"#25d5e4",backgroundColor:"#3b3f5c",pos:"bottom-left",duration:5e3,customClass:"",onActionClick:function(a){a.style.opacity=0},onSecondButtonClick:function(a){}};a.show=function(d){var e=c(!0,b,d);a.current&&(a.current.style.opacity=0,setTimeout(function(){var a=this.parentElement;a&&
// possible null if too many/fast Snackbars
a.removeChild(this)}.bind(a.current),500)),a.snackbar=document.createElement("div"),a.snackbar.className="snackbar-container "+e.customClass,a.snackbar.style.width=e.width;var f=document.createElement("p");if(f.style.margin=0,f.style.padding=0,f.style.color=e.textColor,f.style.fontSize="14px",f.style.fontWeight=300,f.style.lineHeight="1em",f.innerHTML=e.text,a.snackbar.appendChild(f),a.snackbar.style.background=e.backgroundColor,e.showSecondButton){var g=document.createElement("button");g.className="action",g.innerHTML=e.secondButtonText,g.style.color=e.secondButtonTextColor,g.addEventListener("click",function(){e.onSecondButtonClick(a.snackbar)}),a.snackbar.appendChild(g)}if(e.showAction){var h=document.createElement("button");h.className="action",h.innerHTML=e.actionText,h.style.color=e.actionTextColor,h.addEventListener("click",function(){e.onActionClick(a.snackbar)}),a.snackbar.appendChild(h)}e.duration&&setTimeout(function(){a.current===this&&(a.current.style.opacity=0,
// When natural remove event ocurs let's move the snackbar to its origins
a.current.style.top="-100px",a.current.style.bottom="-100px")}.bind(a.snackbar),e.duration),a.snackbar.addEventListener("transitionend",function(b,c){"opacity"===b.propertyName&&"0"===this.style.opacity&&(this.parentElement.removeChild(this),a.current===this&&(a.current=null))}.bind(a.snackbar)),a.current=a.snackbar,document.body.appendChild(a.snackbar);getComputedStyle(a.snackbar).bottom,getComputedStyle(a.snackbar).top;a.snackbar.style.opacity=1,a.snackbar.className="snackbar-container "+e.customClass+" snackbar-pos "+e.pos},a.close=function(){a.current&&(a.current.style.opacity=0)};
// Pure JS Extend
// http://gomakethings.com/vanilla-javascript-version-of-jquery-extend/
var c=function(){var a={},b=!1,c=0,d=arguments.length;"[object Boolean]"===Object.prototype.toString.call(arguments[0])&&(b=arguments[0],c++);for(var e=function(c){for(var d in c)Object.prototype.hasOwnProperty.call(c,d)&&(b&&"[object Object]"===Object.prototype.toString.call(c[d])?a[d]=extend(!0,a[d],c[d]):a[d]=c[d])};c<d;c++){var f=arguments[c];e(f)}return a};return a});
//# sourceMappingURL=snackbar.min.js.map