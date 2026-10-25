// Smart Blood Donation System - Main JavaScript Interactions

document.addEventListener('DOMContentLoaded', function () {
  // 1. Auto-dismiss flash alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  // 2. State to District Cascading Dropdowns
  const stateSelects = document.querySelectorAll('.state-selector');
  stateSelects.forEach(function (stateSelect) {
    const districtSelectId = stateSelect.getAttribute('data-district-target');
    if (!districtSelectId) return;
    const districtSelect = document.getElementById(districtSelectId);
    if (!districtSelect) return;

    stateSelect.addEventListener('change', function () {
      const selectedState = this.value;
      if (!selectedState) {
        districtSelect.innerHTML = '<option value="">-- All Districts --</option>';
        return;
      }

      fetch(`/api/locations/districts?state=${encodeURIComponent(selectedState)}`)
        .then(response => response.json())
        .then(data => {
          districtSelect.innerHTML = '<option value="">-- Select District --</option>';
          if (data.success && data.districts) {
            data.districts.forEach(d => {
              const opt = document.createElement('option');
              opt.value = d;
              opt.textContent = d;
              districtSelect.appendChild(opt);
            });
          }
        })
        .catch(err => console.error("Error fetching districts:", err));
    });
  });

  // 3. Mark in-app notification as read
  const notifItems = document.querySelectorAll('.btn-mark-notif-read');
  notifItems.forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const notifId = this.getAttribute('data-notif-id');
      fetch(`/api/notifications/mark-read/${notifId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            const row = document.getElementById(`notif-item-${notifId}`);
            if (row) {
              row.classList.remove('bg-light');
              row.style.opacity = '0.6';
            }
            this.remove();
          }
        });
    });
  });

  // 4. Quick Demo Login autofill buttons
  const demoPills = document.querySelectorAll('.demo-login-fill');
  demoPills.forEach(pill => {
    pill.addEventListener('click', function () {
      const email = this.getAttribute('data-email');
      const pass = this.getAttribute('data-pass');
      const emailInput = document.getElementById('email');
      const passInput = document.getElementById('password');
      if (emailInput && passInput) {
        emailInput.value = email;
        passInput.value = pass;
        emailInput.classList.add('is-valid');
        passInput.classList.add('is-valid');
      }
    });
  });

  // 5. Clear Search Filter Button handler
  const clearBtns = document.querySelectorAll('#clearSearchBtn, #clearFilterEmptyBtn, .btn-clear-search');
  clearBtns.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const form = document.getElementById('findBloodForm');
      if (form) {
        form.reset();
        const bgSelect = document.getElementById('find_blood_group');
        const stateSelect = document.getElementById('find_state');
        const distSelect = document.getElementById('find_district');
        if (bgSelect) bgSelect.value = '';
        if (stateSelect) stateSelect.value = '';
        if (distSelect) {
          distSelect.innerHTML = '<option value="">-- All Districts --</option>';
          distSelect.value = '';
        }
      }
      const targetUrl = this.getAttribute('href') || '/find-blood';
      window.location.href = targetUrl;
    });
  });
});
