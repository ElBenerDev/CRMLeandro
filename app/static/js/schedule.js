document.addEventListener('DOMContentLoaded', function() {
    const scheduleGrid = document.querySelector('.schedule-grid');

    async function loadSchedules() {
        const response = await fetch('/api/schedule');
        const schedules = await response.json();
        updateScheduleGrid(schedules);
    }

    function updateScheduleGrid(schedules) {
        schedules.forEach(schedule => {
            Object.entries(schedule.schedule).forEach(([day, times]) => {
                const block = createScheduleBlock(schedule, day, times);
                const dayColumn = document.querySelector(`.day-column[data-day="${day}"]`);
                dayColumn.appendChild(block);
            });
        });
    }

    function createScheduleBlock(schedule, day, times) {
        const block = document.createElement('div');
        block.className = 'schedule-block';
        block.style.backgroundColor = schedule.color_code;
        block.innerHTML = `
            <strong>${schedule.employee}</strong><br>
            ${times.start_time} - ${times.end_time}
        `;
        return block;
    }

    loadSchedules();
});