// Handle sync to calendar
document.querySelectorAll('.sync-task').forEach(button => {
    button.addEventListener('click', function() {
        const taskId = this.getAttribute('data-task-id');

        fetch(`/sync_task_to_calendar/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while syncing the task.');
        });
    });
});

// Handle remove from calendar
document.querySelectorAll('.remove-task').forEach(button => {
    button.addEventListener('click', function() {
        if (!confirm('Remove this task from Google Calendar?')) return;

        const taskId = this.getAttribute('data-task-id');

        fetch(`/remove_task_from_calendar/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred.');
        });
    });
});