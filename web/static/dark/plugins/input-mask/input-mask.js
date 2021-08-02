$(document).ready(function(){

    // Static Mask

    $('#static-mask1').inputmask("99-9999999");  //static mask
    $('#static-mask2').inputmask({mask: "aa-9999"});  //static mask


    // Dynamic Syntax

    $('#dynamic-syntax-1').inputmask("9-a{1,3}9{1,3}"); //mask with dynamic syntax
    $('#dynamic-syntax-2').inputmask("aa-9{4}");  //static mask with dynamic syntax
    $('#dynamic-syntax-3').inputmask("aa-9{1,4}");  //dynamic mask ~ the 9 def can be occur 1 to 4 times


    // Aleternate Mask

    $("#alternate-masks1").inputmask({
      mask: ["99.9", "X"],
      definitions: {
        "X": {
          validator: "[xX]",
          casing: "upper"
        }
      }
    });


    $("#alternate-masks2").inputmask("(99.9)|(X)", {
      definitions: {
        "X": {
          validator: "[xX]",
          casing: "upper"
        }
      }
    });


    // Date 

    $("#date").inputmask("99/99/9999");
    $("#date2").inputmask("99-99-9999");
    $("#date3").inputmask("99 December, 9999");


    // Email

    $("#email").inputmask(
        {
            mask:"*{1,20}[.*{1,20}][.*{1,20}][.*{1,20}]@*{1,20}[.*{2,6}][.*{1,2}]",
            greedy:!1,onBeforePaste:function(m,a){return(m=m.toLowerCase()).replace("mailto:","")},
            definitions:{"*":
                {
                    validator:"[0-9A-Za-z!#$%&'*+/=?^_`{|}~-]",
                    cardinality:1,
                    casing:"lower"
                }
            }
        }
    )

    // IP Address
    $("#ip-add").inputmask({mask:"999.999.999.999"});

    // Phone Number
    $("#ph-number").inputmask({mask:"(999) 999-9999"});

    // Currency
    $("#currency").inputmask({mask:"$999,9999,999.99"});

    /*
    ==================
        METHODS
    ==================
    */


    // On Complete
    $("#oncomplete").inputmask("99/99/9999",{ oncomplete: function(){ $('#oncompleteHelp').css('display', 'block'); } });


    // On InComplete
    $("#onincomplete").inputmask("99/99/9999",{ onincomplete: function(){ $('#onincompleteHelp').css('display', 'block'); } });

    
    // On Cleared
    $("#oncleared").inputmask("99/99/9999",{ oncleared: function(){ $('#onclearedHelp').css('display', 'block'); } });


    // Repeater
    $("#repeater").inputmask({ "mask": "2", "repeat": 4});  // ~ mask "9999999999"
    

    // isComplete

    $("#isComplete").inputmask({mask:"999.999.999.99"})
    $("#isComplete").inputmask("setvalue", "117.247.169.64");
    $('#isComplete').on('focus keyup', function(event) {
        event.preventDefault();
        if($(this).inputmask("isComplete")){
            $('#isCompleteHelp').css('display', 'block');
        }
    });
    $('#isComplete').on('keyup', function(event) {
        event.preventDefault();
        if(!$(this).inputmask("isComplete")){
            $('#isCompleteHelp').css('display', 'none');
        }
    });


    // Set Default Value

    $("#setVal").inputmask({
        mask:"*{1,20}[.*{1,20}][.*{1,20}][.*{1,20}]@*{1,20}[.*{2,6}][.*{1,2}]",
        greedy:!1,onBeforePaste:function(m,a){return(m=m.toLowerCase()).replace("mailto:","")},
        definitions:{"*":
            {
                validator:"[0-9A-Za-z!#$%&'*+/=?^_`{|}~-]",
                cardinality:1,
                casing:"lower"
            }
        }
    })
    $('#setVal').on('focus', function(event) {
        $(this).inputmask("setvalue", 'test@mail.com');
    });


});