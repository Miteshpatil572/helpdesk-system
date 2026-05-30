// LIVE DATE & TIME

function updateDateTime() {

    const now = new Date();

    const options = {

        weekday: 'long',
        year: 'numeric',
        month: 'short',
        day: 'numeric'

    };

    const date = now.toLocaleDateString(
        'en-IN',
        options
    );

    const time = now.toLocaleTimeString();

    const element =
    document.getElementById('datetime');

    if (element) {

        element.innerHTML =
        date + " | " + time;

    }

}

setInterval(updateDateTime, 1000);

updateDateTime();

// DELETE CONFIRM

function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this ticket?"
    );

}
