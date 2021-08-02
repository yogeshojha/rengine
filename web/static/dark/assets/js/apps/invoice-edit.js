var currentDate = new Date();

$('.dropify').dropify({
  messages: { 'default': 'Click to Upload Picture/Logo', 'replace': 'Upload or Drag n Drop' }
});

var f1 = flatpickr(document.getElementById('date'), {
  defaultDate: currentDate,
});

var f2 = flatpickr(document.getElementById('due'), {
  defaultDate: currentDate.setDate(currentDate.getDate() + 5),
});

function deleteItemRow() {
    deleteItem = document.querySelectorAll('.delete-item');
    for (var i = 0; i < deleteItem.length; i++) {
        deleteItem[i].addEventListener('click', function() {
            this.parentElement.parentNode.parentNode.parentNode.remove();
        })
    }
}

function selectableDropdown(getElement, myCallback) {
  var getDropdownElement = getElement;
  for (var i = 0; i < getDropdownElement.length; i++) {
      getDropdownElement[i].addEventListener('click', function() {
        console.log(this)
        console.log(this.parentElement.parentNode.querySelector('.dropdown-toggle > .selectable-text'));
        console.log(this.parentElement);

        var dataValue = this.getAttribute('data-value');
        var dataImage = this.getAttribute('data-img-value');

        if(dataValue === null && dataImage === null) {
          console.warn('No attributes are defined. Kindly define one attribute atleast')
        }
        
        if (dataValue != '' && dataValue != null) {
          this.parentElement.parentNode.querySelector('.dropdown-toggle > .selectable-text').innerText = dataValue;
        }

        if (dataImage != '' && dataImage != null) {
          this.parentElement.parentNode.querySelector('.dropdown-toggle > img').setAttribute('src', dataImage );
        }

        var dropdownValues = {dropdownValue:dataValue, dropdownImage:dataImage};
        myCallback(dropdownValues);
      })
  }
}

function getTaxValue(value) {
    if (value.dropdownValue == 'Deducted') {
        console.log('I am percentage')
        document.querySelector('.tax-rate-deducted').style.display = 'block';
        document.querySelector('.tax-rate-per-item').style.display = 'none';
        document.querySelector('.tax-rate-on-total').style.display = 'none';
    } else if (value.dropdownValue == 'Per Item') {
        console.log('I am Flat Amount')
        document.querySelector('.tax-rate-deducted').style.display = 'none';
        document.querySelector('.tax-rate-per-item').style.display = 'block';
        document.querySelector('.tax-rate-on-total').style.display = 'none';
    } else if (value.dropdownValue == 'On Total') {
        console.log('I am Flat Amount')
        document.querySelector('.tax-rate-deducted').style.display = 'none';
        document.querySelector('.tax-rate-per-item').style.display = 'none';
        document.querySelector('.tax-rate-on-total').style.display = 'block';
    } else if (value.dropdownValue == 'None') {
        console.log('I am None')
        document.querySelector('.tax-rate-deducted').style.display = 'none';
        document.querySelector('.tax-rate-per-item').style.display = 'none';
        document.querySelector('.tax-rate-on-total').style.display = 'none';
    }
}

function getDiscountValue(value) {
    if (value.dropdownValue == 'Percent') {
        console.log('I am percentage')
        document.querySelector('.discount-percent').style.display = 'block';
        document.querySelector('.discount-amount').style.display = 'none';
    } else if (value.dropdownValue == 'Flat Amount') {
        console.log('I am Flat Amount')
        document.querySelector('.discount-amount').style.display = 'block';
        document.querySelector('.discount-percent').style.display = 'none';
    } else if (value.dropdownValue == 'None') {
        console.log('I am None')
        document.querySelector('.discount-percent').style.display = 'none';
        document.querySelector('.discount-amount').style.display = 'none';
    }
}

document.getElementsByClassName('additem')[0].addEventListener('click', function() {
  console.log('dfdf')

  getTableElement = document.querySelector('.item-table');
  currentIndex = getTableElement.rows.length;

  $html = '<tr>'+
  '<td class="delete-item-row">'+
      '<ul class="table-controls">'+
          '<li><a href="javascript:void(0);" class="delete-item" data-toggle="tooltip" data-placement="top" title="" data-original-title="Delete"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-x-circle"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg></a></li>'+
      '</ul>'+
    '</td>'+
    '<td class="description"><input type="text" class="form-control  form-control-sm" placeholder="Item Description"> <textarea class="form-control" placeholder="Additional Details"></textarea></td>'+
    '<td class="rate">'+
        '<input type="text" class="form-control  form-control-sm" placeholder="Price">'+
   ' </td>'+
    '<td class="text-right qty"><input type="text" class="form-control  form-control-sm" placeholder="Quantity"></td>'+
    '<td class="text-right amount"><span class="editable-amount"><span class="currency">$</span> <span class="amount">0.00</span></td>'+
    '<td class="text-center tax">'+
        '<div class="n-chk">'+
            '<label class="new-control new-checkbox new-checkbox-text checkbox-primary" style="height: 18px; margin: 0 auto;">'+
              '<input type="checkbox" class="new-control-input">'+
              '<span class="new-control-indicator"></span><span class="new-chk-content">Tax</span>'+
           ' </label>'+
        '</div>'+
    '</td>'+
    '</tr>';

  $(".item-table tbody").append($html);
  deleteItemRow();

})

deleteItemRow();
selectableDropdown(document.querySelectorAll('.invoice-select .dropdown-item'));
selectableDropdown(document.querySelectorAll('.invoice-tax-select .dropdown-item'), getTaxValue);
selectableDropdown(document.querySelectorAll('.invoice-discount-select .dropdown-item'), getDiscountValue);