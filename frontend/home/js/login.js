const loginForm = document.getElementById("loginForm");

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!email || !password) {
    alert("❌ Please fill in all fields.");
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:5000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      alert("✅ " + data.message);
      localStorage.setItem("userEmail", data.email);
      window.location.href = "home/dashboard.html";
    } else {
      alert("❌ " + data.error);
    }
  } catch (err) {
    console.error(err);
    alert("⚠️ Server error, try again later.");
  }
});
document.addEventListener("DOMContentLoaded", () => {
  const userEmail = localStorage.getItem("userEmail");
  if (userEmail) {
    document.querySelector(".welcome").textContent = `👋 Welcome, ${userEmail}`;
  }
});
document.getElementById("loginForm").addEventListener("submit", (e) => {
  e.preventDefault();
  // For now, skip backend check just to test redirection
  window.location.href = "home/dashboard.js";
});

