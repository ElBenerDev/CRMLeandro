document.addEventListener('DOMContentLoaded', function() {
    // Handle order deletion
    window.deleteOrder = async function(orderId) {
        if (confirm('Are you sure you want to delete this order?')) {
            try {
                const response = await fetch(`/orders/${orderId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    // Remove the order card from DOM
                    const orderCard = document.querySelector(`[data-order-id="${orderId}"]`);
                    orderCard.remove();
                } else {
                    alert('Failed to delete order');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while deleting the order');
            }
        }
    };

    // Handle order status updates
    const statusButtons = document.querySelectorAll('.status-toggle');
    statusButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const orderId = this.dataset.orderId;
            const newStatus = this.dataset.status === 'pending' ? 'completed' : 'pending';

            try {
                const response = await fetch(`/orders/${orderId}/status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ status: newStatus })
                });

                if (response.ok) {
                    // Update the button and status badge
                    this.dataset.status = newStatus;
                    const statusBadge = this.closest('.order-card')
                        .querySelector('.status-badge');
                    statusBadge.textContent = newStatus;
                    statusBadge.className = `status-badge ${newStatus}`;
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to update order status');
            }
        });
    });

    // Form validation
    const orderForm = document.getElementById('orderForm');
    if (orderForm) {
        orderForm.addEventListener('submit', function(e) {
            const amount = document.getElementById('amount').value;
            if (isNaN(amount) || amount <= 0) {
                e.preventDefault();
                alert('Please enter a valid amount');
            }
        });
    }
});