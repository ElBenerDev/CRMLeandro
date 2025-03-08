// Core functionality for stock management
class InventoryManager {
    constructor() {
        this.currentSort = {
            column: null,
            direction: 'asc'
        };
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    async init() {
        this.initializeEventListeners();
        this.initializeModals();
    }

    initializeModals() {
        // Initialize all modals
        const stockMovementModal = document.getElementById('stockMovementModal');
        if (stockMovementModal) {
            // Clean up existing modal instance if any
            const existingModal = bootstrap.Modal.getInstance(stockMovementModal);
            if (existingModal) {
                existingModal.dispose();
            }
            
            // Initialize new modal
            this.stockModal = new bootstrap.Modal(stockMovementModal, {
                backdrop: 'static',
                keyboard: true
            });

            // Handle modal cleanup on hide
            stockMovementModal.addEventListener('hidden.bs.modal', () => {
                document.querySelector('.stock-movement-form')?.reset();
                document.getElementById('movementHistory').innerHTML = '';
                this.cleanupModal();
            });
        }
    }

    cleanupModal() {
        const modalBackdrops = document.getElementsByClassName('modal-backdrop');
        Array.from(modalBackdrops).forEach(backdrop => backdrop.remove());
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    initializeEventListeners() {
        // Stock movement modal handling
        const stockMovementModal = document.getElementById('stockMovementModal');
        const saveMovementBtn = document.getElementById('saveMovement');

        if (stockMovementModal) {
            stockMovementModal.addEventListener('show.bs.modal', (event) => {
                const button = event.relatedTarget;
                const row = button.closest('tr');
                const itemId = row.dataset.itemId;
                const itemName = row.cells[0].textContent;
                
                this.setupStockMovementModal(itemId, itemName);
            });
        }

        if (saveMovementBtn) {
            saveMovementBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleStockMovement();
            });
        }
    }

    async setupStockMovementModal(itemId, itemName) {
        const modal = document.getElementById('stockMovementModal');
        modal.querySelector('.modal-title').textContent = `Modificar Stock: ${itemName}`;
        document.getElementById('moveItemId').value = itemId;
        await this.loadMovementHistory(itemId);
    }

    async handleStockMovement() {
        const itemId = document.getElementById('moveItemId').value;
        const quantity = document.getElementById('moveQuantity').value;
        const notes = document.getElementById('moveNotes').value;

        if (!quantity || !notes) {
            this.showToast('Por favor complete todos los campos', 'danger');
            return;
        }

        try {
            const response = await fetch(`/api/inventory/${itemId}/movement`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    quantity: parseFloat(quantity),
                    notes: notes,
                    movement_type: 'add'
                })
            });

            const data = await response.json();
            if (data.success) {
                // Update UI
                this.updateStockDisplay(itemId, data.new_stock);
                this.showToast('Stock actualizado correctamente', 'success');
                
                // Close modal and reset form
                const modal = bootstrap.Modal.getInstance(document.getElementById('stockMovementModal'));
                if (modal) {
                    modal.hide();
                    this.cleanupModal();
                }
                
                // Refresh movements
                await this.loadMovementHistory(itemId);
            } else {
                throw new Error(data.message || 'Error updating stock');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error al actualizar el stock', 'danger');
        }
    }

    updateStockDisplay(itemId, newStock) {
        const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
        if (row) {
            const stockCell = row.querySelector('.stock-cell');
            const currentStockSpan = stockCell.querySelector('.current-stock');
            if (currentStockSpan) {
                const parsedStock = parseFloat(newStock).toFixed(1);
                currentStockSpan.textContent = parsedStock;
                
                // Update styling
                const minStock = parseFloat(row.dataset.minStock || 0);
                currentStockSpan.classList.remove('stock-critical', 'stock-warning');
                
                if (parsedStock == 0) {
                    currentStockSpan.classList.add('stock-critical');
                } else if (parsedStock <= minStock) {
                    currentStockSpan.classList.add('stock-warning');
                }
            }
        }
    }

    async loadMovementHistory(itemId) {
        try {
            const response = await fetch(`/api/inventory/${itemId}/movements`);
            if (!response.ok) throw new Error('Failed to load movements');
            
            const movements = await response.json();
            const tbody = document.getElementById('movementHistory');
            if (!tbody) return;
            
            tbody.innerHTML = movements.map(movement => `
                <tr>
                    <td>${new Date(movement.timestamp).toLocaleString()}</td>
                    <td>${movement.username}</td>
                    <td class="${movement.quantity > 0 ? 'text-success' : 'text-danger'}">
                        ${movement.quantity > 0 ? '+' : ''}${movement.quantity}
                    </td>
                    <td>${movement.notes || ''}</td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading movements:', error);
            this.showToast('Error al cargar historial', 'danger');
        }
    }

    showToast(message, type = 'success') {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast bg-${type} text-white`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">${type === 'success' ? 'Éxito' : 'Error'}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;

        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
}

// Initialize the inventory manager
const inventoryManager = new InventoryManager();

// Add global error handler for modals
window.addEventListener('error', () => {
    document.body.classList.remove('modal-open');
    const modalBackdrops = document.getElementsByClassName('modal-backdrop');
    Array.from(modalBackdrops).forEach(backdrop => backdrop.remove());
});