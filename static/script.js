// Global array to store selected files
let selectedFiles = [];

// Handle file input changes (incremental file selection)
document.getElementById('documents').addEventListener('change', function () {
    const fileListDiv = document.getElementById('file-list');
    const files = this.files;

    // Add new files to the global array
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!selectedFiles.some(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    }

    // Update the displayed file list
    updateFileList();
});

// Function to update the displayed file list
function updateFileList() {
    const fileListDiv = document.getElementById('file-list');
    fileListDiv.innerHTML = ''; // Clear previous list

    if (selectedFiles.length > 0) {
        const ul = document.createElement('ul');
        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.textContent = file.name;

            // Add a remove button for each file
            const removeBtn = document.createElement('span');
            removeBtn.textContent = '×';
            removeBtn.className = 'remove-file-btn';
            removeBtn.onclick = function () {
                selectedFiles.splice(index, 1); // Remove the file from the array
                updateFileList(); // Re-render the file list
            };

            li.appendChild(removeBtn);
            ul.appendChild(li);
        });
        fileListDiv.appendChild(ul);
    } else {
        fileListDiv.innerHTML = '<p>No files selected.</p>';
    }
}

// Handle form submission with progress bar
document.getElementById('uploadForm').addEventListener('submit', function (e) {
    e.preventDefault();

    if (selectedFiles.length === 0) {
        alert('Please select at least one file.');
        return;
    }

    const formData = new FormData();
    formData.append('customer_name', document.getElementById('customer_name').value);
    formData.append('pages_to_print', document.getElementById('pages_to_print').value);
    formData.append('special_instructions', document.getElementById('special_instructions').value);

    // Append all selected files to the form data
    selectedFiles.forEach((file, index) => {
        formData.append(`documents`, file);
    });

    // Simulate progress bar
    const progressBar = document.getElementById('progressBar');
    const progressContainer = document.getElementById('progressContainer');
    let progress = 0;
    progressContainer.style.display = 'block';

    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = progress + '%';

        if (progress >= 100) {
            clearInterval(interval);

            // Submit the form via AJAX
            fetch('/index', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show confirmation modal
                    const modal = document.getElementById('confirmationModal');
                    modal.style.display = 'flex';

                    // Clear the selected files and file list
                    selectedFiles = [];
                    updateFileList();
                }
            })
            .catch(error => {
                alert('An error occurred while submitting the form.');
            });
        }
    }, 200); // Simulate progress every 200ms
});

// Close confirmation modal
document.getElementById('closeModal').addEventListener('click', function () {
    const modal = document.getElementById('confirmationModal');
    modal.style.display = 'none';
});

// Event delegation for "Mark as Done" and "Remove" buttons in the admin panel
document.addEventListener('click', function (event) {
    // Handle "Mark as Done" button
    if (event.target.classList.contains('mark-done-btn')) {
        const row = event.target.closest('tr');
        const orderId = row.dataset.orderId;

        fetch(`/mark_done/${orderId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Move the row to the "Completed Orders" table
                    const completedTableBody = document.querySelector('#completedOrdersTable tbody');
                    completedTableBody.appendChild(row);

                    // Remove action buttons from the row
                    const actionsCell = row.querySelector('td:last-child');
                    actionsCell.innerHTML = ''; // Clear the buttons
                }
            });
    }

    // Handle "Remove" button
    if (event.target.classList.contains('remove-order-btn')) {
        const row = event.target.closest('tr');
        const orderId = row.dataset.orderId;

        fetch(`/remove_order/${orderId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    row.remove(); // Remove the row from the table
                }
            });
    }
});