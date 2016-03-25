$(function() {
  nod.classes.successClass = 'has-success';
  nod.classes.errorClass = 'has-error';
  
  var n = nod();
  n.configure({
        submit: '.submit-btn',
        disableSubmit: true
  });

  n.add([{
    selector: '#ssid',
    validate: /^[a-z0-9\-]+$/i,
    errorMessage: 'Only alphanumeric symbols and minus sign allowed'
  }, {
    selector: '#ssid',
    validate: 'presence',
    errorMessage: 'Cannot be empty'
  }, {
    selector: '#psk',
    validate: 'between-length:8:30',
    errorMessage: 'Must be between 8 and 30 characters long'
  }, {
    selector: '#psk',
    validate: /^[a-z0-9]+$/i,
    errorMessage: 'Only alphanumeric symbols allowed'
  }, {
    selector: '#start',
    validate: 'presence',
    errorMessage: 'Cannot be empty'
  }, {
    selector: '#stop',
    validate: 'presence',
    errorMessage: 'Cannot be empty'
  }, {
    selector: '#start',
    validate: /^\d{4}[\/\-](0?[1-9]|1[012])[\/\-](0?[1-9]|[12][0-9]|3[01])$/,
    errorMessage: 'Must be in specified format'
  }, {
    selector: '#stop',
    validate: /^\d{4}[\/\-](0?[1-9]|1[012])[\/\-](0?[1-9]|[12][0-9]|3[01])$/,
    errorMessage: 'Must be in specified format'
  }]);

  n.performCheck();
  
     var nowTemp = new Date();
     var now = new Date(nowTemp.getFullYear(), nowTemp.getMonth(), nowTemp.getDate(), 0, 0, 0, 0);

     var checkin = $('#startPicker').datepicker({
         onRender: function (date) {
             return date.valueOf() < now.valueOf() ? 'disabled' : '';
         }
     }).on('changeDate', function (ev) {
         if (ev.date.valueOf() > checkout.date.valueOf()) {
             checkout.setValue(new Date(ev.date));
         } else {
             checkout.fill();
         }
         checkin.hide();
         $('#stopPicker')[0].focus();
     }).data('datepicker');
     var checkout = $('#stopPicker').datepicker({
         onRender: function (date) {
             return date.valueOf() < checkin.date.valueOf() ? 'disabled' : '';
         }
     }).on('changeDate', function (ev) {
         checkout.hide();
     }).data('datepicker');

});
