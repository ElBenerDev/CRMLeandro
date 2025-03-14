class CashRegister {
    constructor() {
        this.currentEntryId = null;
        this.isInitialVerified = false;
        this.isDayStarted = false;
        this.dailyTotals = {
            initial: 200.00,
            sales: 0,
            expenses: 0,
            balance: 200.00
        };
        
        this.vaultTotal = 0;
        this.loadVaultTotal();

        // Initialize immediately
        this.loadInitialData();
        this.initializeEventListeners();
    }

    async loadVaultTotal() {
        try {
            const response = await fetch('/api/cash-register/vault/total');
            if (!response.ok) throw new Error('Failed to load vault total');
            
            const data = await response.json();
            this.vaultTotal = data.total || 0;
            this.updateVaultDisplay();
            console.log('Loaded vault total:', this.vaultTotal); // Debug log
        } catch (error) {
            console.error('Error loading vault total:', error);
            this.showAlert('Error al cargar el total de caja fuerte', 'danger');
        }
    }

    updateVaultDisplay() {
        const vaultDisplay = document.getElementById('vaultTotalDisplay');
        if (vaultDisplay) {
            const formattedTotal = this.formatCurrency(this.vaultTotal || 0);
            console.log('Updating vault display:', formattedTotal); // Debug log
            vaultDisplay.textContent = formattedTotal;
        }
    }

    async updateVaultTotal() {
        try {
            const response = await fetch('/api/cash-register/vault/total');
            if (!response.ok) {
                throw new Error('Error getting vault total');
            }
            const total = await response.json();
            this.updateVaultDisplay(total);
            return total;
        } catch (error) {
            console.error('Error updating vault total:', error);
        }
    }

    loadInitialData() {
        console.log('Loading initial data:', window.initialData);
        
        // Reset state first
        this.isDayStarted = false;
        this.currentEntryId = null;
        this.isInitialVerified = false;
        this.dailyTotals = {
            initial: 200.00,
            sales: 0,
            expenses: 0,
            balance: 200.00
        };
        
        if (window.initialData && window.initialData.currentRegister) {
            const register = window.initialData.currentRegister;
            
            // Only set active state if register is open
            if (register.status === 'open') {
                this.currentEntryId = register._id;
                this.isInitialVerified = register.initial_amount_verified;
                this.isDayStarted = true;
                this.dailyTotals = {
                    initial: register.initial_amount_counted,
                    sales: register.total_income || 0,
                    expenses: register.total_expenses || 0,
                    balance: register.current_balance || register.initial_amount_counted
                };
            }

            // Update UI states
            document.getElementById('startDayBtn').disabled = register.status === 'open';
            document.getElementById('addTransactionBtn').disabled = register.status !== 'open';
            document.getElementById('closeDayBtn').disabled = register.status !== 'open';
            document.getElementById('dailyStatusCard').style.display = register.status === 'open' ? 'block' : 'none';
            
            // Update displays if register is open
            if (register.status === 'open') {
                this.updateDailyStatus();
                this.updateTransactionsTable(register.transactions || []);
            }
        } else {
            console.log('No current register found');
            // Reset UI for new day
            document.getElementById('startDayBtn').disabled = false;
            document.getElementById('addTransactionBtn').disabled = true;
            document.getElementById('closeDayBtn').disabled = true;
            document.getElementById('dailyStatusCard').style.display = 'none';
        }
    }

    initializeEventListeners() {
        // Start Day verification
        const verifyAndStartBtn = document.getElementById('verifyAndStartBtn');
        verifyAndStartBtn?.addEventListener('click', () => this.startDay());

        // Transaction handling
        const addTransactionBtn = document.getElementById('addTransactionBtn');
        const saveTransactionBtn = document.getElementById('saveTransactionBtn');
        addTransactionBtn?.addEventListener('click', () => this.showTransactionModal());
        saveTransactionBtn?.addEventListener('click', () => this.saveTransaction());

        // Close day handling
        const closeDayBtn = document.getElementById('closeDayBtn');
        const confirmCloseBtn = document.getElementById('confirmCloseBtn');
        closeDayBtn?.addEventListener('click', () => this.showCloseDayModal());
        confirmCloseBtn?.addEventListener('click', () => this.closeDay());

        // Initial amount verification
        const initialAmountInput = document.getElementById('initial_amount_counted');
        initialAmountInput?.addEventListener('input', () => this.checkInitialAmount());

        // Add export button handler
        const exportBtn = document.querySelector('button[onclick="exportToExcel()"]');
        exportBtn?.addEventListener('click', () => this.exportToExcel());
    }

    async startDay() {
        const counted = parseFloat(document.getElementById('initial_amount_counted').value);
        const notes = document.getElementById('startNotes').value;
        const responsible = document.getElementById('responsible').value;

        if (isNaN(counted)) {
            this.showAlert('Por favor ingrese el monto contado', 'danger');
            return;
        }

        try {
            const response = await fetch('/api/cash-register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    date: new Date().toISOString(),
                    initial_amount_counted: counted,
                    initial_amount_verified: true,
                    initial_count_time: new Date().toISOString(),
                    notes: notes,
                    responsible: responsible,
                    status: 'open'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error starting day');
            }

            const result = await response.json();
            this.currentEntryId = result.id;
            this.isInitialVerified = true;
            this.isDayStarted = true;
            this.dailyTotals.initial = counted;
            this.dailyTotals.balance = counted;

            // Update UI
            document.getElementById('startDayBtn').disabled = true;
            this.updateDailyStatus();
            document.getElementById('dailyStatusCard').style.display = 'block';
            document.getElementById('addTransactionBtn').disabled = false;
            document.getElementById('closeDayBtn').disabled = false;

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('startDayModal'));
            modal.hide();

            this.showAlert('Día iniciado correctamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            this.showAlert(error.message || 'Error al iniciar el día', 'danger');
        }
    }

    checkInitialAmount() {
        const counted = parseFloat(document.getElementById('initial_amount_counted').value) || 0;
        const expected = 200.00;
        const difference = counted - expected;
        const statusDiv = document.getElementById('initialAmountStatus');

        if (counted === expected) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> Monto verificado correctamente
                </div>`;
            document.getElementById('verifyAndStartBtn').disabled = false;
        } else {
            statusDiv.innerHTML = `
                <div class="alert ${Math.abs(difference) < 5 ? 'alert-warning' : 'alert-danger'}">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Diferencia detectada:</strong> ${this.formatCurrency(difference)}
                    ${difference > 0 ? '(Sobrante)' : '(Faltante)'}
                </div>`;
            document.getElementById('verifyAndStartBtn').disabled = true;
        }
    }

    async saveTransaction() {
        const type = document.querySelector('input[name="transactionType"]:checked').value;
        const amount = parseFloat(document.getElementById('amount').value);
        const description = document.getElementById('description').value;

        if (isNaN(amount) || amount <= 0) {
            this.showAlert('Por favor ingrese un monto válido', 'danger');
            return;
        }

        if (!description) {
            this.showAlert('Por favor ingrese una descripción', 'danger');
            return;
        }

        try {
            const response = await fetch(`/api/cash-register/${this.currentEntryId}/transactions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type,
                    amount,
                    description
                })
            });

            if (!response.ok) throw new Error('Transaction failed');

            const result = await response.json();
            console.log('Transaction result:', result);

            // Update transactions array and daily totals
            window.initialData.transactions = result.transactions;
            
            // Calculate daily totals
            this.dailyTotals.sales = 0;
            this.dailyTotals.expenses = 0;
            result.transactions.forEach(t => {
                if (t.type === 'income') {
                    this.dailyTotals.sales += t.amount;
                } else {
                    this.dailyTotals.expenses += t.amount;
                }
            });
            
            this.dailyTotals.balance = this.dailyTotals.initial + 
                                     this.dailyTotals.sales - 
                                     this.dailyTotals.expenses;

            // Update UI
            this.updateDailyStatus();
            this.updateTransactionsTable(result.transactions);

            // Keep current vault total and add new transaction
            if (type === 'income') {
                this.vaultTotal += amount;
            } else {
                this.vaultTotal -= amount;
            }
            this.updateVaultDisplay();

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('transactionModal'));
            modal.hide();
            document.getElementById('transactionForm').reset();

            this.showAlert('Transacción guardada correctamente', 'success');

        } catch (error) {
            console.error('Error:', error);
            this.showAlert(error.message || 'Error al guardar la transacción', 'danger');
        }
    }

    async addTransaction(type, amount, description) {
        try {
            const response = await fetch(`/api/cash-register/${this.currentEntryId}/transactions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, amount, description })
            });

            if (!response.ok) {
                throw new Error('Error adding transaction');
            }

            const result = await response.json();
            console.log('Transaction result:', result);

            // Update transactions table
            this.updateTransactionsTable(result.transactions);
            
            // Update daily totals
            if (type === 'income') {
                this.dailyTotals.sales += amount;
            } else {
                this.dailyTotals.expenses += amount;
            }
            this.updateDailyStatus();

            // Get updated vault total without resetting
            await this.updateVaultTotal();

            return result;
        } catch (error) {
            console.error('Error:', error);
            this.showAlert(error.message || 'Error adding transaction', 'danger');
            throw error;
        }
    }

    updateDailyStatus() {
        document.getElementById('initialCountDisplay').textContent = 
            this.formatCurrency(this.dailyTotals.initial);
        document.getElementById('salesDisplay').textContent = 
            this.formatCurrency(this.dailyTotals.sales);
        document.getElementById('expensesDisplay').textContent = 
            this.formatCurrency(this.dailyTotals.expenses);
        document.getElementById('currentBalanceDisplay').textContent = 
            this.formatCurrency(this.dailyTotals.balance);
    }

    updateTransactionsTable(transactions = []) {
        const tbody = document.getElementById('transactionsTableBody');
        let runningBalance = this.dailyTotals.initial;
        
        // Sort transactions by time
        const sortedTransactions = [...transactions].sort((a, b) => 
            new Date(a.time) - new Date(b.time)
        );

        tbody.innerHTML = sortedTransactions.map(t => {
            // Calculate running balance
            if (t.type === 'income') {
                runningBalance += t.amount;
            } else {
                runningBalance -= t.amount;
            }

            // Format time
            const time = new Date(t.time).toLocaleTimeString('es-AR', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });

            return `
                <tr class="${t.type === 'income' ? 'table-success' : 'table-danger'} align-middle">
                    <td class="text-nowrap">${time}</td>
                    <td>
                        <span class="badge ${t.type === 'income' ? 'bg-success' : 'bg-danger'}">
                            ${t.type === 'income' ? 'INGRESO' : 'GASTO'}
                        </span>
                    </td>
                    <td>${t.description}</td>
                    <td class="text-end fw-bold">
                        ${t.type === 'income' ? '+' : '-'}${this.formatCurrency(t.amount)}
                    </td>
                    <td class="text-end fw-bold">${this.formatCurrency(runningBalance)}</td>
                    <td class="text-nowrap">${t.recorded_by || ''}</td>
                </tr>
            `;
        }).join('');

        // Show empty state if no transactions
        if (sortedTransactions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <i class="fas fa-info-circle me-2"></i>
                        No hay transacciones registradas
                    </td>
                </tr>
            `;
        }
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount)); // Use Math.abs to handle negative numbers
    }

    showAlert(message, type) {
        // Find alert container or create it if it doesn't exist
        let alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.style.position = 'fixed';
            alertContainer.style.top = '20px';
            alertContainer.style.right = '20px';
            alertContainer.style.zIndex = '1050';
            document.body.appendChild(alertContainer);
        }

        // Create alert
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add alert to container
        alertContainer.appendChild(alert);

        // Initialize Bootstrap alert
        const bsAlert = new bootstrap.Alert(alert);

        // Remove after 5 seconds
        setTimeout(() => {
            bsAlert.close();
            // Remove from DOM after animation
            alert.addEventListener('closed.bs.alert', () => alert.remove());
        }, 5000);
    }

    showTransactionModal() {
        // Reset form
        document.getElementById('transactionForm').reset();
        // Set default type to income
        document.getElementById('typeIncome').checked = true;
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('transactionModal'));
        modal.show();
    }

    showCloseDayModal() {
        const expectedBalance = this.dailyTotals.balance;
        document.getElementById('expectedBalance').textContent = 
            this.formatCurrency(expectedBalance);
        document.getElementById('final_count').value = '';
        document.getElementById('closeNotes').value = '';
        
        const modal = new bootstrap.Modal(document.getElementById('closeDayModal'));
        modal.show();
    }

    async closeDay() {
        const finalCount = parseFloat(document.getElementById('final_count').value);
        const notes = document.getElementById('closeNotes').value;

        if (isNaN(finalCount)) {
            this.showAlert('Por favor ingrese el monto final', 'danger');
            return;
        }

        try {
            const response = await fetch(`/api/cash-register/${this.currentEntryId}/close`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    final_count: finalCount,
                    notes: notes
                })
            });

            if (!response.ok) throw new Error('Error closing day');

            const result = await response.json();
            console.log('Close day result:', result); // Debug log

            // Update vault total if provided
            if (result.vault_total !== undefined) {
                this.vaultTotal = result.vault_total;
                this.updateVaultDisplay();
                console.log('Final vault total:', this.vaultTotal); // Debug log
            }

            // Disable controls
            document.getElementById('addTransactionBtn').disabled = true;
            document.getElementById('closeDayBtn').disabled = true;

            // Enable startDayBtn after successful close
            document.getElementById('startDayBtn').disabled = false;
            this.isDayStarted = false;

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('closeDayModal'));
            modal.hide();

            this.showAlert('Día cerrado correctamente', 'success');

            // Reload page after 2 seconds
            setTimeout(() => window.location.reload(), 2000);

        } catch (error) {
            console.error('Error:', error);
            this.showAlert('Error al cerrar el día', 'danger');
        }
    }

    async exportToExcel() {
        if (!this.currentEntryId) {
            // Check if there's a register in window.initialData
            if (window.initialData && window.initialData.currentRegister) {
                this.currentEntryId = window.initialData.currentRegister._id;
            } else {
                this.showAlert('No hay datos para exportar', 'warning');
                return;
            }
        }

        try {
            const format = 'xlsx';
            const response = await fetch(`/api/cash-register/${this.currentEntryId}/export?format=${format}`, {
                method: 'GET'
            });

            if (!response.ok) throw new Error('Error al exportar datos');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const date = new Date().toISOString().split('T')[0];
            a.href = url;
            a.download = `reporte_caja_${date}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

            this.showAlert('Reporte exportado correctamente', 'success');
        } catch (error) {
            console.error('Error:', error);
            this.showAlert('Error al exportar el reporte', 'danger');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.cashRegister = new CashRegister();
});

// Add the export function globally
window.exportToExcel = function() {
    if (window.cashRegister) {
        window.cashRegister.exportToExcel();
    } else {
        console.error('Cash register not initialized');
    }
};