// all the functions and event listeners for the notification panel

// this is to check and compare the last notification id with the current notification id
let lastNotificationId = null;
let isInitialLoad = true;

function updateNotifications() {
  let api_url = "/api/notifications/";
  const currentProjectSlug = getCurrentProjectSlug();
  if (currentProjectSlug) {
    api_url += `?project_slug=${currentProjectSlug}`;
  }
  fetch(api_url, {
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

      if (data.length === 0) {
        const noNotificationsMessage = document.createElement("div");
        noNotificationsMessage.className =
          "notification-panel-item d-flex align-items-center justify-content-center p-3";
        noNotificationsMessage.innerHTML = `
            <p class="text-muted mb-0">Ping? Pong! No notifications, moving along</p>
        `;
        notificationPanel.appendChild(noNotificationsMessage);
      } else {
        // decisive part to show the Snackbar
        if (!isInitialLoad && data[0].id !== lastNotificationId) {
          showNotificationSnackbar(data[0]);
        }
        lastNotificationId = data[0].id;

        data.forEach((notification) => {
          const notificationItem = document.createElement("div");
          notificationItem.className = `notification-panel-item d-flex align-items-start p-3 ${
            notification.is_read ? "" : "notification-panel-unread"
          } notification-panel-status-${notification.status}`;
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
                        <small class="notification-panel-time">${timeago.format(
                          new Date(notification.created_at)
                        )}</small>
                    </div>
                `;
          notificationItem.addEventListener("click", (event) => {
            notificationAction(
              notification.id,
              notification.redirect_link,
              notification.open_in_new_tab
            );
          });
          notificationPanel.appendChild(notificationItem);
        });
      }

      updateUnreadCount();

      // set first load to false
      isInitialLoad = false;
    });
}

function showNotificationSnackbar(notification) {
  let backgroundColor, actionTextColor;

  switch (notification.status) {
    case "error":
      backgroundColor = "#e7515a";
      actionTextColor = "#fff";
      break;
    case "warning":
      backgroundColor = "#e2a03f";
      actionTextColor = "#fff";
      break;
    case "success":
      backgroundColor = "#8dbf42";
      actionTextColor = "#fff";
      break;
    default:
      backgroundColor = "#2196f3";
      actionTextColor = "#fff";
  }

  Snackbar.show({
    text: `New notification: ${notification.title}`,
    pos: "top-right",
    actionTextColor: actionTextColor,
    backgroundColor: backgroundColor,
    duration: 2500,
  });
}

function updateUnreadCount() {
  let api_url = "/api/notifications/unread_count/";
  const currentProjectSlug = getCurrentProjectSlug();
  if (currentProjectSlug) {
    api_url += `?project_slug=${currentProjectSlug}`;
  }
  fetch(api_url, {
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

function notificationAction(notificationId, redirectLink, openInNewTab) {
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

    // this is where we handle all the notification actions such as redirecting to a specific page
    if (redirectLink) {
      if (openInNewTab) {
        window.open(redirectLink, "_blank");
      } else {
        window.location.href = redirectLink;
      }
    }
  });
}

function clearAllNotifications() {
  let api_url = "/api/notifications/clear_all/";
  const currentProjectSlug = getCurrentProjectSlug();
  if (currentProjectSlug) {
    api_url += `?project_slug=${currentProjectSlug}`;
  }
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

  const markAllReadBtn = document.querySelector("#mark-all-read-btn");
  markAllReadBtn.addEventListener("click", markAllAsRead);

  // Update notifications every 15 seconds
  updateNotifications();
  setInterval(updateNotifications, 15000);

  setInterval(updateTimes, 30000);
});

function getCurrentProjectSlug() {
  const hiddenInput = document.querySelector('input[name="current_project"]');
  return hiddenInput ? hiddenInput.value : null;
}

function markAllAsRead() {
  fetch("/api/notifications/mark_all_read/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.ok) {
        document
          .querySelectorAll(".notification-panel-item")
          .forEach((item) => {
            item.classList.remove("notification-panel-unread");
          });
        updateUnreadCount();
      }
    })
    .catch((error) =>
      console.error("Error marking all notifications as read:", error)
    );
}

function updateTimes() {
  document
    .querySelectorAll(".notification-panel-time")
    .forEach((timeElement) => {
      const datetime = timeElement.getAttribute("datetime");
      if (datetime) {
        timeElement.textContent = timeago.format(new Date(datetime));
      }
    });
}
