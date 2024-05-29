document.addEventListener('DOMContentLoaded', function () {
    var status = document.querySelector('meta[name="flash-message"]').getAttribute('content');
    if (status) {
        var modal = new bootstrap.Modal(document.getElementById('paymentStatusModal'));
        document.querySelector('.modal-body').textContent = status;
        modal.show();
    }
});
