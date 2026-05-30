// PIE CHART

function loadPieChart(open, progress, closed) {

    const pie = document.getElementById("pieChart");

    if (pie) {

        new Chart(pie, {

            type: 'pie',

            data: {

                labels: [

                    'Open',
                    'In Progress',
                    'Closed'

                ],

                datasets: [{

                    data: [

                        open,
                        progress,
                        closed

                    ],

                    backgroundColor: [

                        '#ff4d4d',
                        '#ffcc00',
                        '#28a745'

                    ]

                }]

            }

        });

    }

}

// BAR CHART

function loadBarChart(open, progress, closed) {

    const bar = document.getElementById("barChart");

    if (bar) {

        new Chart(bar, {

            type: 'bar',

            data: {

                labels: [

                    'Open',
                    'In Progress',
                    'Closed'

                ],

                datasets: [{

                    label: 'Tickets',

                    data: [

                        open,
                        progress,
                        closed

                    ],

                    backgroundColor: [

                        '#ff4d4d',
                        '#ffcc00',
                        '#28a745'

                    ]

                }]

            }

        });

    }

}