document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('entryModal');
    const form = document.getElementById('cashEntryForm');
    let currentEntryId = null;

    window.openNewEntryModal = function() {
        currentEntryId = null;
        form.reset();
        modal.style.display = 'block';
    }

    window.editEntry = async function(entryId) {
        currentEntryId = entryId;
        try {
            const response = await fetch(`/api/cash-register/${entryId}`);
            const entry = await response.json();
            
            document.getElementById('date').value = entry.date.split('T')[0];
            document.getElementById('income').value = entry.income;
            document.getElementById('expenses').value = entry.expenses;
            document.getElementById('details').value = entry.details || '';
            
            modal.style.display = 'block';
        } catch (error) {
            console.error('Error fetching entry:', error);
        }
    }

    window.deleteEntry = async function(entryId) {
        if (confirm('Are you sure you want to delete this entry?')) {
            try {
                const response = await fetch(`/api/cash-register/${entryId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    location.reload();
                }
            } catch (error) {
                console.error('Error deleting entry:', error);
            }
        }
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            date: document.getElementById('date').value,
            income: parseFloat(document.getElementById('income').value),
            expenses: parseFloat(document.getElementById('expenses').value),
            details: document.getElementById('details').value
        };

        try {
            const url = currentEntryId 
                ? `/api/cash-register/${currentEntryId}`
                : '/api/cash-register';
            
            const method = currentEntryId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                location.reload();
            }
        } catch (error) {
            console.error('Error saving entry:', error);
        }
    });

    // Close modal when clicking the X
    document.querySelector('.close').onclick = function() {
        modal.style.display = 'none';
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    async function loadCashEntries() {
        const response = await fetch('/api/cash-register');
        const entries = await response.json();
        updateCashTable(entries);
    }

    async function saveCashEntry(formData) {
        const response = await fetch('/api/cash-register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        if (response.ok) {
            await loadCashEntries();
            closeModal();
        }
    }

    function updateCashTable(entries) {
        const tbody = document.querySelector('.cash-table tbody');
        tbody.innerHTML = entries.map(entry => `
            <tr>
                <td>${formatDate(entry.date)}</td>
                <td>$${entry.initial_cash.toFixed(2)}</td>
                <td>$${entry.income.toFixed(2)}</td>
                <td>$${entry.expenses.toFixed(2)}</td>
                <td>${entry.details || ''}</td>
                <td>$${entry.safe_balance.toFixed(2)}</td>
                <td>${entry.responsible}</td>
                <td>
                    <button onclick="editEntry('${entry._id}')" class="btn-edit">Edit</button>
                    <button onclick="deleteEntry('${entry._id}')" class="btn-delete">Delete</button>
                </td>
            </tr>
        `).join('');
    }
});