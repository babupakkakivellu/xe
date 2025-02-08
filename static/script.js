// Initialize event handlers when DOM is ready
function initializeEventHandlers() {
    console.log('Initializing event handlers...');

    // Handle Mark as Done
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('mark-done-btn')) {
            e.preventDefault();
            console.log('Mark as Done clicked');
            
            const row = e.target.closest('tr');
            if (!row) {
                console.error('Could not find parent row');
                return;
            }

            const orderId = row.dataset.orderId;
            console.log('Order ID:', orderId);

            // Send request to mark as done
            fetch(`/mark_done/${orderId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Move row to completed table
                    const completedTable = document.querySelector('#completedOrdersTable tbody');
                    if (completedTable) {
                        // Clone the row and remove the actions column
                        const newRow = row.cloneNode(true);
                        const actionsCell = newRow.querySelector('td:last-child');
                        if (actionsCell) {
                            actionsCell.remove();
                        }
                        completedTable.appendChild(newRow);
                        row.remove();
                    }
                } else {
                    alert('Error: ' + (data.message || 'Could not mark as done'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error marking as done');
            });
        }
    });

    // Handle Remove
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('remove-order-btn')) {
            e.preventDefault();
            console.log('Remove clicked');

            if (!confirm('Are you sure you want to remove this order?')) {
                return;
            }

            const row = e.target.closest('tr');
            if (!row) {
                console.error('Could not find parent row');
                return;
            }

            const orderId = row.dataset.orderId;
            console.log('Order ID:', orderId);

            // Send request to remove
            fetch(`/remove_order/${orderId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    row.remove();
                } else {
                    alert('Error: ' + (data.message || 'Could not remove order'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error removing order');
            });
        }
    });

    // Handle file input changes
    const fileInput = document.getElementById('documents');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }

    // Handle form submission
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmission);
    }

    // Handle modal close button
    const closeModalBtn = document.getElementById('closeModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            const modal = document.getElementById('confirmationModal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    }

    console.log('Event handlers initialized');
}

// Global array to store selected files
let selectedFiles = [];

// Handle file selection
function handleFileSelection(event) {
    const fileListDiv = document.getElementById('file-list');
    const files = event.target.files;

    // Add new files to the global array
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!selectedFiles.some(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    }

    updateFileList();
}

// Update the displayed file list
function updateFileList() {
    const fileListDiv = document.getElementById('file-list');
    if (!fileListDiv) return;

    fileListDiv.innerHTML = '';

    if (selectedFiles.length > 0) {
        const ul = document.createElement('ul');
        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.textContent = file.name;

            const removeBtn = document.createElement('span');
            removeBtn.textContent = '×';
            removeBtn.className = 'remove-file-btn';
            removeBtn.onclick = function() {
                selectedFiles.splice(index, 1);
                updateFileList();
            };

            li.appendChild(removeBtn);
            ul.appendChild(li);
        });
        fileListDiv.appendChild(ul);
    } else {
        fileListDiv.innerHTML = '<p>No files selected.</p>';
    }
}

// Handle form submission
function handleFormSubmission(e) {
    e.preventDefault();

    if (selectedFiles.length === 0) {
        alert('Please select at least one file.');
        return;
    }

    const formData = new FormData();
    
    // Add form fields
    const fields = ['customer_name', 'pages_to_print', 'special_instructions'];
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            formData.append(field, element.value);
        }
    });

    // Add files
    selectedFiles.forEach(file => {
        formData.append('documents', file);
    });

    // Show progress bar
    const progressBar = document.getElementById('progressBar');
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }

    // Simulate upload progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }

        if (progress >= 100) {
            clearInterval(interval);
            submitForm(formData);
        }
    }, 200);
}

// Submit form data to server
function submitForm(formData) {
    fetch('/index', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const progressContainer = document.getElementById('progressContainer');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }

        if (data.success) {
            const modal = document.getElementById('confirmationModal');
            if (modal) {
                modal.style.display = 'flex';
            }
            selectedFiles = [];
            updateFileList();
        } else {
            alert(data.message || 'An error occurred while uploading the files.');
        }
    })
    .catch(error => {
        console.error('Error uploading files:', error);
        alert('An error occurred while uploading the files.');
    });
}

// Try both methods to ensure the script runs
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEventHandlers);
} else {
    initializeEventHandlers();
}

// Log when the script loads
console.log('Script loaded');