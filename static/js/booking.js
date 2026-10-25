// Appointment Booking Workflow & Slot Availability Manager

document.addEventListener('DOMContentLoaded', function () {
  const stateInput = document.getElementById('booking_state');
  const districtInput = document.getElementById('booking_district');
  const hospitalSelect = document.getElementById('hospital_id');
  const dateInput = document.getElementById('slot_date');
  const slotsContainer = document.getElementById('slots_container');
  const slotHiddenInput = document.getElementById('selected_slot_time');
  const submitBtn = document.getElementById('btn_submit_booking');
  const hospitalInfoBox = document.getElementById('hospital_info_box');

  if (!hospitalSelect || !dateInput || !slotsContainer) return;

  // Set min date to today and max date to 60 days ahead
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  const minDate = `${yyyy}-${mm}-${dd}`;
  dateInput.min = minDate;

  // Filter hospitals on district change
  if (districtInput) {
    districtInput.addEventListener('change', function () {
      const state = stateInput ? stateInput.value : '';
      const district = this.value;
      if (!district) return;

      fetch(`/api/hospitals?state=${encodeURIComponent(state)}&district=${encodeURIComponent(district)}`)
        .then(res => res.json())
        .then(data => {
          hospitalSelect.innerHTML = '<option value="">-- Choose Hospital / Blood Bank --</option>';
          if (data.hospitals && data.hospitals.length > 0) {
            data.hospitals.forEach(h => {
              const opt = document.createElement('option');
              opt.value = h.id;
              opt.textContent = `${h.name} (${h.facility_type})`;
              opt.setAttribute('data-address', h.address);
              opt.setAttribute('data-phone', h.phone);
              opt.setAttribute('data-hours', h.operating_hours);
              hospitalSelect.appendChild(opt);
            });
            hospitalSelect.disabled = false;
          } else {
            hospitalSelect.innerHTML = '<option value="">No verified blood centers found in this district</option>';
            hospitalSelect.disabled = true;
          }
          resetSlots();
        });
    });
  }

  // Hospital selected
  hospitalSelect.addEventListener('change', function () {
    const selectedOpt = this.options[this.selectedIndex];
    if (this.value && hospitalInfoBox) {
      const addr = selectedOpt.getAttribute('data-address') || '';
      const phone = selectedOpt.getAttribute('data-phone') || '';
      const hours = selectedOpt.getAttribute('data-hours') || '24/7';
      hospitalInfoBox.classList.remove('d-none');
      hospitalInfoBox.innerHTML = `
        <div class="d-flex align-items-center gap-2 mb-1">
          <i class="fa-solid fa-hospital text-danger"></i>
          <strong>${selectedOpt.text}</strong>
        </div>
        <div class="small text-muted"><i class="fa-solid fa-location-dot me-1"></i> ${addr}</div>
        <div class="small text-muted"><i class="fa-solid fa-phone me-1"></i> Helpline: ${phone} | <i class="fa-solid fa-clock ms-1 me-1"></i> Hours: ${hours}</div>
      `;
    } else if (hospitalInfoBox) {
      hospitalInfoBox.classList.add('d-none');
    }
    loadSlotsIfReady();
  });

  // Date changed
  dateInput.addEventListener('change', function () {
    loadSlotsIfReady();
  });

  function resetSlots() {
    slotsContainer.innerHTML = '<div class="text-muted small py-3 text-center"><i class="fa-regular fa-calendar-xmark me-1"></i> Please select a hospital and date first to view real-time available donation slots.</div>';
    if (slotHiddenInput) slotHiddenInput.value = '';
    if (submitBtn) submitBtn.disabled = true;
  }

  function loadSlotsIfReady() {
    const hospitalId = hospitalSelect.value;
    const chosenDate = dateInput.value;

    if (!hospitalId || !chosenDate) {
      resetSlots();
      return;
    }

    slotsContainer.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-danger" role="status"></div>
        <span class="ms-2 small text-muted">Checking real-time slot capacity...</span>
      </div>
    `;

    fetch(`/api/hospitals/${hospitalId}/slots?date=${chosenDate}`)
      .then(res => res.json())
      .then(data => {
        if (!data.success || !data.slots || data.slots.length === 0) {
          slotsContainer.innerHTML = `<div class="alert alert-warning small">No slot schedules configured for this date.</div>`;
          return;
        }

        let html = '<div class="row g-2">';
        data.slots.forEach(s => {
          const isFull = !s.is_available;
          const statusBadge = isFull 
            ? '<span class="badge bg-secondary ms-auto">Full</span>'
            : `<span class="badge bg-success-subtle text-success ms-auto">${s.remaining}/${s.capacity} left</span>`;

          html += `
            <div class="col-md-6 col-lg-4">
              <div class="slot-pill-btn d-flex align-items-center justify-content-between ${isFull ? 'disabled' : ''}" 
                   data-slot-time="${s.slot_time}" 
                   data-is-full="${isFull}">
                <div>
                  <div class="fw-semibold small"><i class="fa-regular fa-clock text-danger me-1"></i> ${s.slot_time}</div>
                </div>
                ${statusBadge}
              </div>
            </div>
          `;
        });
        html += '</div>';
        slotsContainer.innerHTML = html;

        // Attach click listener to available slot pills
        const pills = slotsContainer.querySelectorAll('.slot-pill-btn:not(.disabled)');
        pills.forEach(p => {
          p.addEventListener('click', function () {
            pills.forEach(x => x.classList.remove('selected'));
            this.classList.add('selected');
            const slotTime = this.getAttribute('data-slot-time');
            if (slotHiddenInput) slotHiddenInput.value = slotTime;
            if (submitBtn) submitBtn.disabled = false;
          });
        });
      })
      .catch(err => {
        slotsContainer.innerHTML = `<div class="alert alert-danger small">Error checking slots: ${err.message}</div>`;
      });
  }
});
