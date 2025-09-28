// Sidebar Navigation
const navItems = document.querySelectorAll(".sidebar li");
const sections = document.querySelectorAll(".section");

navItems.forEach(item => {
  item.addEventListener("click", () => {
    navItems.forEach(i => i.classList.remove("active"));
    sections.forEach(sec => sec.classList.remove("active"));

    item.classList.add("active");
    document.getElementById(item.dataset.section).classList.add("active");
  });
});

// Theme Toggle
const themeSwitch = document.getElementById("themeSwitch");
themeSwitch.addEventListener("click", () => {
  document.body.classList.toggle("dark");
});

// Charts
new Chart(document.getElementById("taskChart"), {
  type: "doughnut",
  data: {
    labels: ["Completed", "Pending", "In Progress"],
    datasets: [{
      data: [12, 7, 5],
      backgroundColor: ["#10b981", "#f59e0b", "#3b82f6"]
    }]
  },
  options: { plugins: { legend: { position: "bottom" } } }
});

new Chart(document.getElementById("meetingChart"), {
  type: "bar",
  data: {
    labels: ["Mon", "Tue", "Wed", "Thu", "Fri"],
    datasets: [{
      label: "Meetings",
      data: [2, 1, 3, 0, 2],
      backgroundColor: "#4f46e5"
    }]
  },
  options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
});

// Schedule Form
const scheduleForm = document.getElementById("scheduleForm");
const scheduleList = document.getElementById("scheduleList");

scheduleForm?.addEventListener("submit", e => {
  e.preventDefault();
  const title = document.getElementById("meetingTitle").value;
  const date = document.getElementById("meetingDate").value;
  const time = document.getElementById("meetingTime").value;

  const li = document.createElement("li");
  li.textContent = `${title} — ${date} at ${time}`;
  scheduleList.appendChild(li);

  scheduleForm.reset();
});

// Tasks
const taskForm = document.getElementById("taskForm");
const taskList = document.getElementById("taskList");

taskForm?.addEventListener("submit", e => {
  e.preventDefault();
  const task = document.getElementById("taskInput").value;

  const li = document.createElement("li");
  li.textContent = task;
  taskList.appendChild(li);

  taskForm.reset();
});
