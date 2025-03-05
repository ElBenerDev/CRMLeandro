document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing inventory controls');

    // Get necessary elements
    const editButtons = document.querySelectorAll('.edit-stock');
    const saveButtons = document.querySelectorAll('.save-stock');
    const startCountBtn = document.getElementById('startCount');

    console.log('Elements found:', {
        editButtonsCount: editButtons.length,
        saveButtonsCount: saveButtons.length,
        startCountExists: !!startCountBtn
    });

    // Add click handlers to edit buttons
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            console.log('Edit button clicked');
            const row = this.closest('tr');
            const stockCell = row.querySelector('.stock-cell');
            
            // Show input field
            stockCell.querySelector('.stock-value').classList.add('d-none');
            stockCell.querySelector('.stock-edit').classList.remove('d-none');
            
            // Focus the input
            const input = stockCell.querySelector('.stock-input');
            input.focus();
            input.select();
            
            // Disable edit button while editing
            this.disabled = true;
        });
    });

    // Add click handlers to save buttons
    saveButtons.forEach(button => {
        button.addEventListener('click', async function() {
            console.log('Save button clicked');
            const row = this.closest('tr');
            const itemId = row.dataset.itemId;
            const stockCell = row.querySelector('.stock-cell');
            const input = stockCell.querySelector('.stock-input');
            const newStock = parseFloat(input.value);

            if (isNaN(newStock) || newStock < 0) {
                showToast('Por favor ingrese un número válido', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/inventory/${itemId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        current_stock: newStock
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to update');
                }

                const data = await response.json();
                
                // Update display
                stockCell.querySelector('.stock-value').textContent = data.new_stock;
                stockCell.querySelector('.stock-value').classList.remove('d-none');
                stockCell.querySelector('.stock-edit').classList.add('d-none');
                row.querySelector('.edit-stock').disabled = false;

                showToast('Stock actualizado correctamente', 'success');
            } catch (error) {
                console.error('Error updating stock:', error);
                showToast('Error al actualizar stock', 'error');
            }
        });
    });

    // Start count button functionality
    if (startCountBtn) {
        startCountBtn.addEventListener('click', function() {
            console.log('Starting count');
            // Show all edit inputs
            document.querySelectorAll('#inventoryTable tr').forEach(row => {
                const stockCell = row.querySelector('.stock-cell');
                if (stockCell) {
                    stockCell.querySelector('.stock-value').classList.add('d-none');
                    stockCell.querySelector('.stock-edit').classList.remove('d-none');
                }
            });
            
            this.disabled = true;
            
            // Add finish button
            const finishBtn = document.createElement('button');
            finishBtn.className = 'btn btn-primary ms-2';
            finishBtn.innerHTML = '<i class="fas fa-check"></i> Finalizar Conteo';
            this.parentNode.insertBefore(finishBtn, this.nextSibling);
            
            finishBtn.addEventListener('click', function() {
                document.querySelectorAll('#inventoryTable tr').forEach(row => {
                    const stockCell = row.querySelector('.stock-cell');
                    if (stockCell) {
                        stockCell.querySelector('.stock-value').classList.remove('d-none');
                        stockCell.querySelector('.stock-edit').classList.add('d-none');
                    }
                });
                
                startCountBtn.disabled = false;
                this.remove();
                
                showToast('Conteo finalizado', 'success');
            });
        });
    }
});

function showToast(message, type = 'success') {
    const toastContainer = document.querySelector('.toast-container') || (() => {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    })();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type}`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    new bootstrap.Toast(toast).show();
}