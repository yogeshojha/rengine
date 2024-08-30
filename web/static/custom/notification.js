// notifications.js
// all the functions and event listeners for the notification panel

function updateNotifications() {
  fetch("/api/notifications/", {
    method: "GET",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      const notificationPanel = document.querySelector(
        ".notification-panel-body"
      );
      notificationPanel.innerHTML = "";

      data.forEach((notification) => {
        const notificationItem = document.createElement("div");
        notificationItem.className = `notification-panel-item d-flex align-items-start p-3 ${
          notification.is_read ? "" : "notification-panel-unread"
        }`;
        notificationItem.innerHTML = `
                    <div class="notification-panel-content flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="notification-panel-title mb-0">${
                              notification.title
                            }</h6>
                            <span class="notification-panel-icon">
                                <i class="mdi ${notification.icon}"></i>
                            </span>
                        </div>
                        <p class="notification-panel-description mb-1">${
                          notification.description
                        }</p>
                        <small class="notification-panel-time">${new Date(
                          notification.created_at
                        ).toLocaleString()}</small>
                    </div>
                `;
        notificationItem.addEventListener("click", () =>
          notificationAction(notification.id)
        );
        notificationPanel.appendChild(notificationItem);
      });

      updateUnreadCount();
    });
}

function updateUnreadCount() {
  fetch("/api/notifications/unread_count/", {
    method: "GET",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      const badge = document.querySelector("#notification-counter");
      badge.textContent = data.count;
      badge.style.display = data.count > 0 ? "inline-block" : "none";
    });
}

function notificationAction(notificationId) {
  // depending on notification we may also need to redirect to a specific page
  // for example if the notification is related to scan, we may take to scan detail page

  // eithrways mark the notification as read
  fetch(`/api/notifications/${notificationId}/mark_read/`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  }).then(() => {
    updateNotifications();
  });
}

function clearAllNotifications() {
  fetch("/api/notifications/clear_all/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  }).then(() => {
    updateNotifications();
  });
}

// Set up event listeners
document.addEventListener("DOMContentLoaded", () => {
  const clearAllLink = document.querySelector("#clear-notif-btn");
  clearAllLink.addEventListener("click", clearAllNotifications);

  // Update notifications every 30 seconds
  updateNotifications();
  setInterval(updateNotifications, 30000);
});
