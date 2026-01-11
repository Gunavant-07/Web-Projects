document.addEventListener('DOMContentLoaded', () => {
    loadCategory('my-day'); // Default category on load
    loadCustomLists();
    loadCompletedTasks();
    checkDueDateNotifications();

    // Set interval to check due dates every minute
    setInterval(checkDueDateNotifications, 60000);

    // Add click event to load first custom list or 'tasks' when Customize Tasks is clicked
    document.getElementById('tasks').addEventListener('click', async () => {
        document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('selected'));
        document.getElementById('tasks').classList.add('selected');
        const customLists = await loadCustomLists();
        if (customLists.length > 0) {
            loadCategory(customLists[0].list_name); // Load first custom list
        } else {
            loadCategory('tasks'); // Fallback to default tasks
        }
    });

    // Add click event to open profile picture dialog
    document.getElementById('profile-pic').addEventListener('click', openProfilePicDialog);

    // Add event listener for file input change to preview image
    document.getElementById('profile-pic-input').addEventListener('change', previewImage);
});

async function checkDueDateNotifications() {
    try {
        const selectedCategory = document.querySelector('.menu-item.selected') || 
                               document.querySelector('.custom-menu-item.selected');
        let category = selectedCategory ? (selectedCategory.id || selectedCategory.getAttribute('data-list-name')) : 'my-day';

        const response = await fetch(`/get_tasks/${category}`);
        if (!response.ok) throw new Error('Failed to fetch tasks');
        const tasks = await response.json();

        const now = new Date();
        tasks.forEach(task => {
            if (!task.due_date) return;

            const dueDate = new Date(task.due_date);
            const timeDiff = dueDate - now;
            const isOverdue = timeDiff < 0;
            const isDueSoon = timeDiff > 0 && timeDiff <= 24 * 60 * 60 * 1000; // Within 24 hours

            if (isOverdue || isDueSoon) {
                showNotification(task.title, task.due_date, isOverdue, category, task.id);
            }
        });
    } catch (error) {
        console.error('Error checking due date notifications:', error);
    }
}

// Function to show browser notification with click handler
function showNotification(taskTitle, dueDate, isOverdue, category, taskId) {
    if (!("Notification" in window)) {
        console.log("This browser does not support desktop notifications.");
        return;
    }

    if (Notification.permission === "granted") {
        const notification = new Notification(`Task Reminder: ${taskTitle}`, {
            body: `Due: ${new Date(dueDate).toLocaleDateString()} ${isOverdue ? '(Overdue!)' : '(Due Soon!)'}`,
            icon: '/static/icon.png', // Optional: Add a custom icon path
            tag: taskId // Unique tag to avoid duplicate notifications
        });

        // Add click event handler
        notification.onclick = () => {
            console.log(`Notification clicked for task ${taskId}`);
            window.focus(); // Bring window to focus
            loadCategory(category); // Load the category containing the task
            // Optionally, scroll to the task or highlight it (requires task DOM element)
            setTimeout(() => {
                const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
                if (taskElement) {
                    taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    taskElement.classList.add('highlight');
                    setTimeout(() => taskElement.classList.remove('highlight'), 2000); // Remove highlight after 2s
                }
            }, 500);
            notification.close(); // Close the notification after click
        };
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(permission => {
            if (permission === "granted") {
                const notification = new Notification(`Task Reminder: ${taskTitle}`, {
                    body: `Due: ${new Date(dueDate).toLocaleDateString()} ${isOverdue ? '(Overdue!)' : '(Due Soon!)'}`,
                    icon: '/static/icon.png',
                    tag: taskId
                });

                notification.onclick = () => {
                    console.log(`Notification clicked for task ${taskId}`);
                    window.focus();
                    loadCategory(category);
                    setTimeout(() => {
                        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
                        if (taskElement) {
                            taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            taskElement.classList.add('highlight');
                            setTimeout(() => taskElement.classList.remove('highlight'), 2000);
                        }
                    }, 500);
                    notification.close();
                };
            }
        });
    }
}

// Existing functions (loadCategory, loadCustomLists, etc.) remain the same
// Ensure loadCategory and task rendering include data-task-id
// async function loadCategory(category) {
//     try {
//         const response = await fetch(`/get_tasks/${category}`);
//         if (!response.ok) throw new Error('Failed to fetch tasks');
//         const tasks = await response.json();

//         const taskList = document.getElementById('task-list');
//         taskList.innerHTML = '';

//         tasks.forEach(task => {
//             const taskItem = document.createElement('div');
//             taskItem.className = 'task-item';
//             taskItem.setAttribute('data-task-id', task.id); // Add task ID for targeting
//             taskItem.innerHTML = `
//                 <input type="checkbox" ${task.completed ? 'checked' : ''} onchange="toggleTask(${task.id})">
//                 <span>${task.title}</span>
//                 ${task.due_date ? `<span class="due-date">Due: ${new Date(task.due_date).toLocaleDateString()}</span>` : ''}
//                 <i class="fas ${task.important ? 'fa-star' : 'fa-star-o'}" onclick="toggleImportant(${task.id})"></i>
//                 <i class="fas fa-trash-alt" onclick="deleteTask(${task.id})"></i>
//             `;
//             taskList.appendChild(taskItem);
//         });

//         // Make task list sortable
//         new Sortable(taskList, {
//             animation: 150,
//             onEnd: updateTaskOrder
//         });
//     } catch (error) {
//         console.error('Error loading category:', error);
//     }
// }

//==============================================================================================================================
async function loadCategory(category) {
    try {
        const response = await fetch(`/get_tasks/${category}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch tasks');
        }
        const tasks = await response.json();
        renderTasks(tasks, category);
    } catch (error) {
        console.error('Error loading category:', error);
        alert(`Error loading tasks: ${error.message}. Please try again later.`);
    }
}

async function loadCustomLists() {
    try {
        const response = await fetch('/get_custom_lists');
        if (!response.ok) throw new Error('Failed to fetch custom lists');
        const lists = await response.json();
        renderCustomLists(lists);
        return lists;
    } catch (error) {
        console.error('Error loading custom lists:', error);
        return [];
    }
}

async function loadCompletedTasks() {
    try {
        const response = await fetch('/get_tasks/completed');
        if (!response.ok) throw new Error('Failed to fetch completed tasks');
        const tasks = await response.json();
        renderCompletedTasks(tasks);
    } catch (error) {
        console.error('Error loading completed tasks:', error);
    }
}

function renderTasks(tasks, category) {
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = '';

    if (tasks.length === 0) {
        const noTasks = document.createElement('p');
        noTasks.textContent = `No tasks in ${category}.`;
        taskList.appendChild(noTasks);
        return;
    }

    tasks.forEach(task => {
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item';
        taskItem.setAttribute('data-id', task.id);
        if (task.completed) taskItem.classList.add('completed');

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'task-checkbox';
        checkbox.checked = task.completed;
        checkbox.addEventListener('change', () => toggleTask(task.id, category));
        taskItem.appendChild(checkbox);

        const taskText = document.createElement('span');
        taskText.className = 'task-text';
        taskText.textContent = task.title;
        taskItem.appendChild(taskText);

        if (task.due_date) {
            const dueDate = document.createElement('span');
            dueDate.className = 'due-date';
            dueDate.textContent = `Due: ${new Date(task.due_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`;
            taskItem.appendChild(dueDate);
        }

        const starIcon = document.createElement('i');
        starIcon.className = task.important ? 'fas fa-star star-icon' : 'far fa-star star-icon';
        starIcon.setAttribute('data-task-id', task.id);
        starIcon.style.cursor = 'pointer';
        starIcon.style.color = task.important ? '#ffd700' : '#ccc';
        starIcon.addEventListener('click', () => toggleImportant(task.id, category));
        taskItem.appendChild(starIcon);

        const removeIcon = document.createElement('i');
        removeIcon.className = 'fas fa-times delete-task';
        removeIcon.style.cursor = 'pointer';
        removeIcon.addEventListener('click', () => deleteTask(task.id, category));
        taskItem.appendChild(removeIcon);

        taskList.appendChild(taskItem);
    });

    new Sortable(taskList, {
        animation: 150,
        handle: '.task-item',
        onEnd: async (evt) => {
            const taskOrder = Array.from(taskList.children)
                .filter(child => child.classList.contains('task-item'))
                .map(child => child.getAttribute('data-id'));
            try {
                const response = await fetch('/update_task_order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_order: taskOrder }),
                });
                if (!response.ok) throw new Error('Failed to update task order');
            } catch (error) {
                console.error('Error updating task order:', error);
                alert('Failed to update task order. Please try again.');
            }
        }
    });
}

function renderCompletedTasks(tasks) {
    const completedList = document.getElementById('completed-tasks-list');
    completedList.innerHTML = '';
    tasks.forEach(task => {
        const li = document.createElement('li');
        li.innerHTML = `<i class="fas fa-check-circle"></i> ${task.title} <span>Completed ${new Date(task.updated_at).toLocaleDateString()}</span>`;
        completedList.appendChild(li);
    });
}

async function toggleTask(taskId, category) {
    try {
        const response = await fetch(`/toggle_task/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) throw new Error('Failed to toggle task');
        loadCategory(category);
        loadCompletedTasks();
    } catch (error) {
        console.error('Error toggling task:', error);
        alert('Failed to toggle task. Please try again.');
    }
}

async function toggleImportant(taskId, category) {
    try {
        const response = await fetch(`/toggle_important/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to toggle important');
        }
        const data = await response.json();
        const taskItem = document.querySelector(`.task-item[data-id="${taskId}"]`);
        if (taskItem) {
            const starIcon = taskItem.querySelector('i.star-icon');
            if (starIcon) {
                if (data.important) {
                    starIcon.className = 'fas fa-star star-icon';
                    starIcon.style.color = '#ffd700';
                } else {
                    starIcon.className = 'far fa-star star-icon';
                    starIcon.style.color = '#ccc';
                }
            }
        } else {
            console.warn(`Task item for task ${taskId} not found in current view`);
        }
        loadCategory(category);
    } catch (error) {
        console.error('Error toggling important:', error);
        alert(`Failed to toggle important status: ${error.message}`);
    }
}

async function deleteTask(taskId, category) {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'Do you want to delete this task?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel'
    });

    if (result.isConfirmed) {
        try {
            const response = await fetch(`/delete_task/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) throw new Error('Failed to delete task');
            loadCategory(category);
            loadCompletedTasks();
            Swal.fire('Deleted!', 'The task has been deleted.', 'success');
        } catch (error) {
            console.error('Error deleting task:', error);
            Swal.fire('Error', 'Failed to delete task. Please try again.', 'error');
        }
    }
}

function renderCustomLists(lists) {
    const customListsContainer = document.getElementById('custom-lists');
    customListsContainer.innerHTML = '';

    lists.forEach(list => {
        const listItem = document.createElement('div');
        listItem.className = 'menu-item custom-menu-item';
        listItem.setAttribute('data-list-name', list.list_name);
        listItem.innerHTML = `
            <i class="fas fa-list"></i> ${list.list_name}
            <i class="fas fa-trash-alt remove-list"></i>
        `;
        listItem.onclick = (e) => {
            if (!e.target.classList.contains('remove-list')) {
                loadCategory(list.list_name);
                document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('selected'));
                listItem.classList.add('selected');
            }
        };
        listItem.querySelector('.remove-list').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent the category load event
            deleteCustomList(list.list_name);
        });
        customListsContainer.appendChild(listItem);
    });
}

async function deleteCustomList(listName) {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'Do you want to delete this custom list? All tasks in this list, including important ones, will be deleted.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel'
    });

    if (result.isConfirmed) {
        try {
            const response = await fetch('/delete_custom_list', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ list_name: listName }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to delete custom list');
            }
            loadCustomLists();
            const selectedCategory = document.querySelector('.custom-menu-item.selected');
            if (selectedCategory && selectedCategory.getAttribute('data-list-name') === listName) {
                loadCategory('tasks'); // Switch to Tasks if the deleted list was selected
            }
            // Reload the "Important" category to reflect the deletion of tasks
            loadCategory('important');
            Swal.fire('Deleted!', 'The custom list and all its tasks have been deleted.', 'success');
        } catch (error) {
            console.error('Error deleting custom list:', error);
            Swal.fire('Error', `Failed to delete custom list: ${error.message}`, 'error');
        }
    }
}

function showNewListInput() {
    const inputContainer = document.getElementById('new-list-input-container');
    inputContainer.style.display = 'block';
}

async function createCustomList() {
    const listInput = document.getElementById('new-list-input');
    const listName = listInput.value.trim();

    if (!listName) {
        alert('Please enter a list name.');
        return;
    }

    try {
        const response = await fetch('/add_custom_list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ list_name: listName }),
        });
        if (!response.ok) throw new Error('Failed to create list');
        listInput.value = '';
        document.getElementById('new-list-input-container').style.display = 'none';
        loadCustomLists();
    } catch (error) {
        console.error('Error creating custom list:', error);
        alert('Failed to create list. Please try again.');
    }
}

document.getElementById('add-task-btn').addEventListener('click', async () => {
    const taskInput = document.getElementById('task-input');
    const dueDateInput = document.getElementById('due-date-input');
    const taskTitle = taskInput.value.trim();
    const dueDate = dueDateInput.value;

    if (!taskTitle) {
        alert('Please enter a task.');
        return;
    }

    const selectedCategory = document.querySelector('.menu-item.selected') || document.querySelector('.custom-menu-item.selected');
    if (!selectedCategory) {
        alert('Please select a category.');
        return;
    }

    let category = selectedCategory.id || selectedCategory.getAttribute('data-list-name');
    if (category === 'important') {
        const { value: selectedCategory } = await Swal.fire({
            title: 'Select a category',
            input: 'select',
            inputOptions: {
                'my-day': 'My Day',
                'planned': 'Planned',
                'tasks': 'Tasks'
            },
            inputPlaceholder: 'Select a category',
            showCancelButton: true,
        });
        if (!selectedCategory) return;
        category = selectedCategory;
    }
    console.log('Adding task to category:', category);

    try {
        const response = await fetch('/add_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: taskTitle, category: category, due_date: dueDate }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to add task');
        }
        taskInput.value = '';
        dueDateInput.value = '';
        loadCategory(category);
    } catch (error) {
        console.error('Error adding task:', error);
        alert(`Failed to add task: ${error.message}. Please try again.`);
    }
});

document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
        const category = item.id || item.getAttribute('data-list-name');
        loadCategory(category);
    });
});

// Profile Picture Functions
function openProfilePicDialog() {
    const dialog = document.getElementById('profile-pic-dialog');
    dialog.showModal();
}

function closeProfilePicDialog() {
    const dialog = document.getElementById('profile-pic-dialog');
    dialog.close();
    document.getElementById('profile-pic-input').value = ''; // Clear file input
}

function previewImage(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const previewImage = document.getElementById('preview-image');
            previewImage.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

async function uploadProfilePic() {
    const fileInput = document.getElementById('profile-pic-input');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select an image to upload.');
        return;
    }

    const formData = new FormData();
    formData.append('profile_pic', file);

    try {
        const response = await fetch('/update_profile_pic', {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to update profile picture');
        }
        const data = await response.json();
        document.getElementById('profile-pic').src = data.profile_pic; // Update profile pic
        document.getElementById('preview-image').src = data.profile_pic; // Update preview
        closeProfilePicDialog();
        Swal.fire('Success!', 'Profile picture updated successfully.', 'success');
    } catch (error) {
        console.error('Error uploading profile picture:', error);
        Swal.fire('Error', `Failed to update profile picture: ${error.message}`, 'error');
    }
}