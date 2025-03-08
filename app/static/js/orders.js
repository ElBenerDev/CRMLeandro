function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
}

function initializeOrderButtons() {
    const orderConfirmModal = new bootstrap.Modal(document.getElementById('orderConfirmModal'));
    let currentItemId = null;

    // Individual order buttons
    document.querySelectorAll('.create-order').forEach(button => {
        button.addEventListener('click', function() {
            const data = this.dataset;
            currentItemId = data.itemId;
            
            document.getElementById('orderItemName').textContent = data.itemName;
            document.querySelector('.order-details').innerHTML = `
                <div class="alert alert-info">
                    <strong>Current Stock:</strong> ${data.currentStock} ${data.unit}<br>
                    <strong>Suggested Order:</strong> +${data.suggestedOrder} ${data.unit}
                </div>
            `;
            
            orderConfirmModal.show();
        });
    });

    // Order all buttons
    document.querySelectorAll('.order-all-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const supplier = this.dataset.supplier;
            if (confirm(`Create orders for all items from ${supplier}?`)) {
                try {
                    const response = await fetch('/api/orders/create-bulk', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ supplier: supplier })
                    });
                    
                    if (response.ok) {
                        showToast('Orders created successfully', 'success');
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        throw new Error('Failed to create orders');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('Error creating orders', 'danger');
                }
            }
        });
    });

    // Confirm order button
    document.getElementById('confirmOrder').addEventListener('click', async function() {
        if (!currentItemId) return;
        
        try {
            const response = await fetch('/api/orders/create-from-suggestion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ item_id: currentItemId })
            });
            
            if (response.ok) {
                orderConfirmModal.hide();
                showToast('Order created successfully', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error('Failed to create order');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error creating order', 'danger');
        }
    });
}

function showToast(message, type = 'success') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.group('Orders Page Initialization');
    try {
        console.log('Initializing orders page...');
        initializeTooltips();
        initializeOrderButtons();
        console.log('Orders page initialized successfully');
    } catch (error) {
        console.error('Error initializing orders page:', error);
    }
    console.groupEnd();
});