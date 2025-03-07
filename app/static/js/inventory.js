document.addEventListener('DOMContentLoaded', function() {
    console.group('Inventory Page Initialization');
    
    const container = document.querySelector('.daily-cash-container');
    console.log('Container found:', !!container);
    
    if (!container) {
        console.error('Container not found');
        console.groupEnd();
        return;
    }

    // Get state from data attributes with debug logging
    const pageState = {
        isAdmin: container.dataset.isAdmin === 'true',
        isCountDay: container.dataset.isCountDay === 'true',
        isCounting: container.dataset.isCounting === 'true'
    };

    console.log('Raw data attributes:', {
        isAdmin: container.dataset.isAdmin,
        isCountDay: container.dataset.isCountDay,
        isCounting: container.dataset.isCounting
    });
    
    console.log('Parsed page state:', pageState);
    console.log('Button should show:', !pageState.isAdmin && pageState.isCountDay && !pageState.isCounting);

    // Initialize all controls
    initializeStockControls();
    initializeUserControls(pageState);
    if (pageState.isAdmin) {
        initializeAdminControls();
    }

    console.groupEnd();
});

async function handleStartCount() {
    try {
        const modal = new bootstrap.Modal(document.getElementById('weeklyCountModal'));
        modal.show();

        // Initialize difference calculations
        const inputs = document.querySelectorAll('.counted-stock');
        inputs.forEach(input => {
            input.addEventListener('input', calculateDifference);
        });

        // Handle form submission
        const submitBtn = document.getElementById('submitCount');
        submitBtn.addEventListener('click', handleWeeklyCountSubmit);

    } catch (error) {
        console.error('Error:', error);
        showToast('Error al iniciar conteo', 'danger');
    }
}

function initializeUserControls(pageState) {
    console.log('Initializing user controls:', pageState);
    
    const startWeeklyCountBtn = document.getElementById('startWeeklyCount');
    if (startWeeklyCountBtn) {
        console.log('Found weekly count button');
        startWeeklyCountBtn.addEventListener('click', handleStartCount);
    } else {
        console.log('Weekly count button not found');
    }
}

function initializeAdminControls() {
    console.log('Initializing admin controls');
    const editButtons = document.querySelectorAll('.edit-item');
    const addItemButton = document.querySelector('#addItemButton');

    if (addItemButton) {
        addItemButton.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('addItemModal'));
            modal.show();
        });
    }

    editButtons.forEach(button => {
        button.addEventListener('click', handleEditItem);
    });
}

async function handleWeeklyCountSubmit() {
    try {
        const rows = document.querySelectorAll('#weeklyCountForm tr[data-item-id]');
        const items = Array.from(rows).map(row => ({
            item_id: row.dataset.itemId,
            current_stock: parseFloat(row.querySelector('.current-stock').textContent),
            counted_stock: parseFloat(row.querySelector('.counted-stock').value) || 0
        })).filter(item => !isNaN(item.counted_stock));

        const notes = document.getElementById('countNotes').value;

        if (items.length === 0) {
            showToast('Por favor ingrese al menos un conteo', 'warning');
            return;
        }

        const response = await fetch('/api/inventory/weekly-count', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                items: items,
                notes: notes
            })
        });

        if (!response.ok) {
            throw new Error('Failed to submit count');
        }

        const data = await response.json();
        showToast('Conteo semanal guardado correctamente', 'success');
        
        // Reload page after successful submission
        setTimeout(() => window.location.reload(), 1500);

    } catch (error) {
        console.error('Error:', error);
        showToast('Error al guardar conteo', 'danger');
    }
}

async function handleStockUpdate(event) {
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
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_stock: newStock
            })
        });

        if (response.ok) {
            const data = await response.json();
            updateStockDisplay(row, data.new_stock);
            showToast('Stock actualizado correctamente', 'success');
        } else {
            throw new Error('Failed to update stock');
        }
    } catch (error) {
        console.error('Error updating stock:', error);
        showToast('Error al actualizar stock', 'error');
    }
}

function calculateDifference(event) {
    const row = event.target.closest('tr');
    const currentStock = parseFloat(row.querySelector('.current-stock').textContent);
    const countedStock = parseFloat(event.target.value) || 0;
    const difference = countedStock - currentStock;
    
    const differenceCell = row.querySelector('.difference');
    differenceCell.textContent = difference.toFixed(2);
    
    // Add visual feedback
    differenceCell.classList.remove('text-success', 'text-danger');
    if (difference > 0) {
        differenceCell.classList.add('text-success');
    } else if (difference < 0) {
        differenceCell.classList.add('text-danger');
    }
}

function showToast(message, type = 'success') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type}`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function initializeStockControls() {
    const updateButtons = document.querySelectorAll('.update-stock');
    
    updateButtons.forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            const stockCell = row.querySelector('.stock-cell');
            const stockSpan = stockCell.querySelector('.current-stock');
            const currentStock = parseFloat(stockSpan.textContent);
            
            // Create input group with Bootstrap styling
            const inputGroup = document.createElement('div');
            inputGroup.className = 'input-group input-group-sm';
            
            // Create input
            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'form-control';
            input.value = currentStock;
            input.step = '0.01';
            input.min = '0';
            
            // Create buttons container
            const btnGroup = document.createElement('div');
            btnGroup.className = 'input-group-append';
            
            // Create save button
            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn btn-success';
            saveBtn.innerHTML = '<i class="fas fa-check"></i>';
            saveBtn.title = 'Guardar';
            
            // Create cancel button
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-danger';
            cancelBtn.innerHTML = '<i class="fas fa-times"></i>';
            cancelBtn.title = 'Cancelar';
            
            // Assemble the input group
            btnGroup.appendChild(saveBtn);
            btnGroup.appendChild(cancelBtn);
            inputGroup.appendChild(input);
            inputGroup.appendChild(btnGroup);
            
            // Store original content
            const originalContent = stockCell.innerHTML;
            
            // Replace content with input group
            stockCell.innerHTML = '';
            stockCell.appendChild(inputGroup);
            
            // Focus input
            input.focus();
            input.select();
            
            // Handle save
            saveBtn.addEventListener('click', async function() {
                const newStock = parseFloat(input.value);
                if (isNaN(newStock) || newStock < 0) {
                    showToast('Por favor ingrese un número válido', 'danger');
                    return;
                }
                
                try {
                    const response = await fetch(`/api/inventory/${row.dataset.itemId}/update-stock`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ current_stock: newStock })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        stockCell.innerHTML = originalContent;
                        stockCell.querySelector('.current-stock').textContent = newStock;
                        showToast('Stock actualizado correctamente', 'success');
                    } else {
                        throw new Error('Failed to update stock');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('Error al actualizar stock', 'danger');
                    stockCell.innerHTML = originalContent;
                }
            });
            
            // Handle cancel
            cancelBtn.addEventListener('click', function() {
                stockCell.innerHTML = originalContent;
            });
        });
    });
}

function initializeSorting() {
    const headers = document.querySelectorAll('th.sortable');
    let currentSort = {
        column: null,
        direction: 'asc'
    };

    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            
            // Reset other headers
            headers.forEach(h => {
                if (h !== header) {
                    h.classList.remove('asc', 'desc');
                }
            });

            // Toggle sort direction
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                header.classList.toggle('asc', currentSort.direction === 'asc');
                header.classList.toggle('desc', currentSort.direction === 'desc');
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
                header.classList.add('asc');
            }

            sortTable(column, currentSort.direction);
        });
    });
}

function sortTable(column, direction) {
    const tbody = document.getElementById('inventoryTableBody');
    const rows = Array.from(tbody.getElementsByTagName('tr'));

    const sortedRows = rows.sort((a, b) => {
        let aVal = getCellValue(a, column);
        let bVal = getCellValue(b, column);

        // Convert to numbers for numerical columns
        if (column === 'stock' || column === 'min_stock' || column === 'max_stock') {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }

        if (aVal === bVal) return 0;
        
        if (direction === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });

    // Clear and re-append rows
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }
    
    sortedRows.forEach(row => tbody.appendChild(row));
}

function getCellValue(row, column) {
    const columnMap = {
        'name': 0,
        'stock': 1,
        'supplier': 3,
        'category': 4,
        'min_stock': 5,
        'max_stock': 6
    };

    const cell = row.cells[columnMap[column]];
    
    // Handle stock cell special case
    if (column === 'stock') {
        const stockSpan = cell.querySelector('.current-stock');
        return stockSpan ? stockSpan.textContent.trim() : '0';
    }
    
    return cell.textContent.trim().toLowerCase();
}