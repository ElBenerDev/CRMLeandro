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

        this.searchTimeout = null;
        this.searchResults = [];
        this.isAdmin = document.querySelector('.daily-cash-container').dataset.isAdmin === 'true';
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

        // Add search functionality
        const searchInput = document.getElementById('searchInventory');
        if (searchInput) {
            // Create results container if it doesn't exist
            let searchResults = document.querySelector('.search-results');
            if (!searchResults) {
                searchResults = document.createElement('div');
                searchResults.className = 'search-results';
                searchInput.parentNode.appendChild(searchResults);
            }

            // Add input event listener
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                const query = e.target.value.trim();
                
                if (query.length >= 2) {
                    this.searchTimeout = setTimeout(() => {
                        this.performSearch(query);
                    }, 300);
                } else {
                    searchResults.style.display = 'none';
                }
            });

            // Close results when clicking outside
            document.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                    searchResults.style.display = 'none';
                }
            });
        }

        // Add Item Modal Handling
        const addItemBtn = document.getElementById('saveNewItem');
        if (addItemBtn) {
            addItemBtn.addEventListener('click', () => this.handleAddItem());
        }

        // Supplier-Category Auto Selection
        const supplierSelect = document.querySelector('select[name="supplier"]');
        if (supplierSelect) {
            supplierSelect.addEventListener('change', (e) => {
                const supplier = e.target.value;
                const categorySelect = document.querySelector('select[name="category"]');
                const defaultCategory = this.getDefaultCategoryForSupplier(supplier);
                if (defaultCategory && categorySelect) {
                    categorySelect.value = defaultCategory;
                }
            });
        }

        // Add sorting functionality
        const sortableHeaders = document.querySelectorAll('th.sortable');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', () => this.handleSort(header));
        });

        // Add category edit functionality
        document.addEventListener('click', (e) => {
            if (e.target.closest('.edit-category')) {
                const row = e.target.closest('tr');
                const itemId = row.dataset.itemId;
                const currentCategory = row.querySelector('.category-display').textContent.trim();
                this.showCategoryModal(itemId, currentCategory);
            }
        });

        // Add save category button handler
        const saveCategoryBtn = document.getElementById('saveCategoryBtn');
        if (saveCategoryBtn) {
            saveCategoryBtn.addEventListener('click', () => this.handleCategorySave());
        }

        // Set Stock Modal handling
        const setStockModal = document.getElementById('setStockModal');
        if (setStockModal) {
            setStockModal.addEventListener('show.bs.modal', (event) => {
                const button = event.relatedTarget;
                const itemId = button.dataset.itemId;
                const itemName = button.dataset.itemName;
                
                setStockModal.querySelector('.modal-title').textContent = `Modificar Stock Total: ${itemName}`;
                document.getElementById('setItemId').value = itemId;
                
                // Get current stock value
                const row = button.closest('tr');
                const currentStock = parseFloat(row.querySelector('.current-stock').textContent);
                document.getElementById('setStockQuantity').value = currentStock;
            });

            const saveSetStockBtn = document.getElementById('saveSetStock');
            if (saveSetStockBtn) {
                saveSetStockBtn.addEventListener('click', () => this.handleSetStock());
            }
        }

        // Only show edit buttons to admin users
        if (!this.isAdmin) {
            // Hide admin-only buttons
            document.querySelectorAll('.edit-category, .stock-set').forEach(btn => {
                btn.style.display = 'none';
            });
        }

        // Regular users can only add stock
        if (!this.isAdmin) {
            document.querySelectorAll('.stock-update').forEach(btn => {
                btn.title = 'Agregar Stock';
            });
        }

        // Add weekly count button handler
        const startWeeklyCountBtn = document.getElementById('startWeeklyCount');
        if (startWeeklyCountBtn) {
            startWeeklyCountBtn.addEventListener('click', () => this.startWeeklyCount());
        }

        // Add save weekly count handler
        const saveWeeklyCountBtn = document.getElementById('saveWeeklyCount');
        if (saveWeeklyCountBtn) {
            saveWeeklyCountBtn.addEventListener('click', () => this.saveWeeklyCount());
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

    async handleSetStock() {
        try {
            const itemId = document.getElementById('setItemId').value;
            const newStock = parseFloat(document.getElementById('setStockQuantity').value);
            const notes = document.getElementById('setStockNotes').value;

            if (isNaN(newStock) || !notes) {
                this.showToast('Por favor complete todos los campos', 'danger');
                return;
            }

            const response = await fetch(`/api/inventory/${itemId}/set-stock`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    new_stock: newStock,
                    notes: notes
                })
            });

            const data = await response.json();
            
            if (data.success) {
                // Update UI
                this.updateStockDisplay(itemId, data.new_stock);
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('setStockModal'));
                if (modal) {
                    modal.hide();
                    this.cleanupModal();
                }
                
                this.showToast('Stock actualizado correctamente', 'success');
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

    async performSearch(query) {
        try {
            const response = await fetch(`/api/inventory/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search failed');
            
            const results = await response.json();
            this.displaySearchResults(results);
        } catch (error) {
            console.error('Search error:', error);
            this.showToast('Error en la búsqueda', 'danger');
        }
    }

    displaySearchResults(results) {
        const searchResults = document.querySelector('.search-results');
        if (!searchResults) return;

        if (results.length === 0) {
            searchResults.innerHTML = '<div class="no-results">No se encontraron resultados</div>';
            searchResults.style.display = 'block';
            return;
        }

        const html = results.map(item => `
            <div class="search-result-item" data-item-id="${item.id}">
                <div class="item-name">${item.name}</div>
                <div class="item-details">
                    <span class="badge bg-secondary">${item.supplier}</span>
                    <span class="badge bg-info">${item.category}</span>
                    <span class="badge ${this.getStockBadgeClass(item.current_stock)}">
                        Stock: ${item.current_stock} ${item.unit}
                    </span>
                </div>
            </div>
        `).join('');

        searchResults.innerHTML = html;
        searchResults.style.display = 'block';

        // Add click handlers to results
        const resultItems = searchResults.querySelectorAll('.search-result-item');
        resultItems.forEach(item => {
            item.addEventListener('click', () => this.handleSearchResultClick(item));
        });
    }

    getStockBadgeClass(stock) {
        if (stock <= 0) return 'bg-danger';
        if (stock <= 5) return 'bg-warning text-dark';
        return 'bg-success';
    }

    handleSearchResultClick(resultItem) {
        const itemId = resultItem.dataset.itemId;
        const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
        
        if (row) {
            // Hide search results
            document.querySelector('.search-results').style.display = 'none';
            
            // Clear search input
            document.getElementById('searchInventory').value = '';
            
            // Highlight and scroll to the row
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            row.classList.add('highlight');
            setTimeout(() => row.classList.remove('highlight'), 2000);
        }
    }

    getDefaultCategoryForSupplier(supplier) {
        const supplierCategoryMap = {
            'ACACIAS': 'PERECEDEROS',
            'AMAZON': 'INSUMOS BÁSICOS',
            'CARLOS ROLLOS PACK': 'PACKAGING',
            'COSTCO': 'INSUMOS BÁSICOS',
            'DEPOT': 'EQUIPO',
            'INSTACAR': 'INSUMOS BÁSICOS',
            'LIZ': 'LIMPIEZA',
            'MARIANO': 'PERECEDEROS',
            'ROMANO': 'BEBIDAS',
            'SANBER': 'BEBIDAS',
            'SYSCO': 'INSUMOS BÁSICOS',
            'TQMUCH': 'CONDIMENTOS',
            'WALLMART': 'INSUMOS BÁSICOS',
            'WEBRESTAURANT': 'EQUIPO'
        };
        return supplierCategoryMap[supplier] || '';
    }

    async handleAddItem() {
        try {
            const form = document.getElementById('addItemForm');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Validate required fields
            const requiredFields = ['name', 'unit', 'supplier', 'category'];
            for (const field of requiredFields) {
                if (!data[field]) {
                    this.showToast(`El campo ${field} es requerido`, 'danger');
                    return;
                }
            }

            // Convert numeric fields BEFORE sending to ensure proper values
            data.current_stock = parseFloat(data.current_stock) || 0;
            data.min_stock = parseFloat(data.min_stock) || 0;
            data.max_stock = parseFloat(data.max_stock) || 0;

            const response = await fetch('/api/inventory/items', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error adding item');
            }

            const result = await response.json();

            // Store the form values before closing the modal
            const itemData = {
                _id: result._id,
                name: data.name,
                current_stock: data.current_stock,
                unit: data.unit,
                supplier: data.supplier,
                category: data.category,
                min_stock: data.min_stock,
                max_stock: data.max_stock
            };

            // Close modal first
            const modalElement = document.getElementById('addItemModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            modal.hide();
            
            // Remove modal backdrop and cleanup
            this.cleanupModal();

            // Reset form
            form.reset();

            // Add new row to table with the stored values
            setTimeout(() => {
                this.addItemToTable(itemData);
                this.showToast('Item agregado correctamente', 'success');
            }, 300);

        } catch (error) {
            console.error('Error adding item:', error);
            this.showToast(error.message || 'Error al agregar item', 'danger');
        }
    }

    addItemToTable(item) {
        const tbody = document.getElementById('inventoryTableBody');
        if (!tbody) return;

        // Ensure all numeric values are properly parsed
        const currentStock = parseFloat(item.current_stock || 0);
        const minStock = parseFloat(item.min_stock || 0);
        const maxStock = parseFloat(item.max_stock || 0);

        const row = document.createElement('tr');
        row.dataset.itemId = item._id;
        row.dataset.minStock = minStock;

        row.innerHTML = `
            <td>${item.name}</td>
            <td class="stock-cell">
                <span class="current-stock ${this.getStockClass(currentStock, minStock)}">
                    ${currentStock.toFixed(1)}
                </span>
            </td>
            <td>${item.unit}</td>
            <td>${item.supplier}</td>
            <td class="category-cell">
                <span class="category-display">${item.category}</span>
                ${document.querySelector('.daily-cash-container').dataset.isAdmin === 'true' ? `
                    <button class="btn btn-sm btn-link edit-category" title="Editar categoría">
                        <i class="fas fa-edit"></i>
                    </button>
                ` : ''}
            </td>
            <td>${minStock.toFixed(1)}</td>
            <td>${maxStock.toFixed(1)}</td>
            <td class="text-center">
                <button class="btn btn-outline-primary btn-sm stock-update" 
                        data-bs-toggle="modal" 
                        data-bs-target="#stockMovementModal"
                        data-item-id="${item._id}"
                        data-item-name="${item.name}"
                        title="Modificar Stock">
                    <i class="fas fa-cubes"></i>
                </button>
            </td>
        `;

        tbody.insertBefore(row, tbody.firstChild);
        row.classList.add('highlight');
        setTimeout(() => row.classList.remove('highlight'), 2000);
    }

    getStockClass(currentStock, minStock) {
        if (currentStock === 0) return 'stock-critical';
        if (currentStock <= minStock) return 'stock-warning';
        return '';
    }

    handleSort(header) {
        const column = header.dataset.sort;
        const direction = this.currentSort.column === column && 
                         this.currentSort.direction === 'asc' ? 'desc' : 'asc';

        // Update sort indicators
        document.querySelectorAll('th.sortable').forEach(th => {
            th.classList.remove('asc', 'desc', 'active');
        });
        header.classList.add(direction, 'active');

        // Store current sort
        this.currentSort = { column, direction };

        // Get all rows
        const tbody = document.getElementById('inventoryTableBody');
        const rows = Array.from(tbody.querySelectorAll('tr'));

        // Sort rows
        const sortedRows = this.sortRows(rows, column, direction);

        // Clear and append sorted rows
        tbody.innerHTML = '';
        sortedRows.forEach(row => tbody.appendChild(row));
    }

    sortRows(rows, column, direction) {
        return rows.sort((a, b) => {
            let aValue, bValue;

            switch (column) {
                case 'name':
                    aValue = a.cells[0].textContent.trim().toLowerCase();
                    bValue = b.cells[0].textContent.trim().toLowerCase();
                    break;
                case 'stock':
                    aValue = parseFloat(a.cells[1].querySelector('.current-stock').textContent);
                    bValue = parseFloat(b.cells[1].querySelector('.current-stock').textContent);
                    break;
                case 'supplier':
                    aValue = a.cells[3].textContent.trim().toLowerCase();
                    bValue = b.cells[3].textContent.trim().toLowerCase();
                    break;
                case 'category':
                    aValue = a.cells[4].querySelector('.category-display').textContent.trim().toLowerCase();
                    bValue = a.cells[4].querySelector('.category-display').textContent.trim().toLowerCase();
                    break;
                case 'min_stock':
                    aValue = parseFloat(a.cells[5].textContent);
                    bValue = parseFloat(b.cells[5].textContent);
                    break;
                case 'max_stock':
                    aValue = parseFloat(a.cells[6].textContent);
                    bValue = parseFloat(b.cells[6].textContent);
                    break;
                default:
                    return 0;
            }

            // Handle numeric sorting
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return direction === 'asc' ? aValue - bValue : bValue - aValue;
            }

            // Handle string sorting
            return direction === 'asc' 
                ? aValue.localeCompare(bValue) 
                : bValue.localeCompare(aValue);
        });
    }

    showCategoryModal(itemId, currentCategory) {
        const modal = document.getElementById('categoryModal');
        const categorySelect = modal.querySelector('#categorySelect');
        
        // Store item ID for later use
        modal.dataset.itemId = itemId;
        
        // Set current category as selected
        if (categorySelect) {
            categorySelect.value = currentCategory;
        }

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    async handleCategorySave() {
        try {
            const modal = document.getElementById('categoryModal');
            const itemId = modal.dataset.itemId;
            const categorySelect = modal.querySelector('#categorySelect');
            const newCategory = categorySelect.value;

            if (!newCategory) {
                this.showToast('Por favor seleccione una categoría', 'warning');
                return;
            }

            const response = await fetch(`/api/inventory/${itemId}/category`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ category: newCategory })
            });

            if (!response.ok) {
                throw new Error('Failed to update category');
            }

            // Update UI
            const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
            if (row) {
                const categoryDisplay = row.querySelector('.category-display');
                if (categoryDisplay) {
                    categoryDisplay.textContent = newCategory;
                }
            }

            // Close modal
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
            this.cleanupModal();

            this.showToast('Categoría actualizada correctamente', 'success');

        } catch (error) {
            console.error('Error updating category:', error);
            this.showToast('Error al actualizar la categoría', 'danger');
        }
    }

    async startWeeklyCount() {
        try {
            const tbody = document.getElementById('weeklyCountTable');
            tbody.innerHTML = '';

            // Get all inventory items
            const rows = Array.from(document.querySelectorAll('#inventoryTableBody tr'));
            
            rows.forEach(row => {
                const itemId = row.dataset.itemId;
                const name = row.cells[0].textContent;
                const currentStock = parseFloat(row.querySelector('.current-stock').textContent);
                const unit = row.cells[2].textContent;
                const minStock = parseFloat(row.dataset.minStock);

                const tr = document.createElement('tr');
                tr.dataset.itemId = itemId;
                tr.innerHTML = `
                    <td>${name}</td>
                    <td>${currentStock}</td>
                    <td>
                        <input type="number" class="form-control form-control-sm counted-stock" 
                               value="${currentStock}" step="0.1" min="0">
                    </td>
                    <td>${unit}</td>
                    <td>${minStock}</td>
                    <td class="status"></td>
                `;

                tbody.appendChild(tr);

                // Add input handler for real-time status update
                const input = tr.querySelector('.counted-stock');
                input.addEventListener('input', () => {
                    const counted = parseFloat(input.value) || 0;
                    const status = tr.querySelector('.status');
                    if (counted <= 0) {
                        status.innerHTML = '<span class="badge bg-danger">Sin Stock</span>';
                    } else if (counted <= minStock) {
                        status.innerHTML = '<span class="badge bg-warning text-dark">Bajo Mínimo</span>';
                    } else {
                        status.innerHTML = '<span class="badge bg-success">OK</span>';
                    }
                });

                // Trigger initial status
                input.dispatchEvent(new Event('input'));
            });

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('weeklyCountModal'));
            modal.show();

        } catch (error) {
            console.error('Error starting weekly count:', error);
            this.showToast('Error al iniciar el conteo semanal', 'danger');
        }
    }

    async saveWeeklyCount() {
        try {
            const rows = Array.from(document.querySelectorAll('#weeklyCountTable tr'));
            const notes = document.getElementById('weeklyCountNotes').value;
            
            const items = rows.map(row => ({
                item_id: row.dataset.itemId,
                current_stock: parseFloat(row.cells[1].textContent),
                counted_stock: parseFloat(row.querySelector('.counted-stock').value) || 0
            }));

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

            if (!response.ok) throw new Error('Failed to save count');
            
            const result = await response.json();

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('weeklyCountModal'));
            modal.hide();
            this.cleanupModal();

            // Update UI with new stock values
            items.forEach(item => {
                this.updateStockDisplay(item.item_id, item.counted_stock);
            });

            this.showToast('Conteo semanal guardado correctamente', 'success');

            // Show additional message if items need reordering
            if (result.items_below_min > 0) {
                this.showToast(
                    `${result.items_below_min} items necesitan reorden`, 
                    'warning'
                );
            }

        } catch (error) {
            console.error('Error saving weekly count:', error);
            this.showToast('Error al guardar el conteo semanal', 'danger');
        }
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