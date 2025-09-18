/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";

class ProjectDashboard extends Component {
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        // Get project_id from context
        const context = this.props.action?.context || {};
        this.projectId = context.project_id;

        this.state = useState({
            loading: true,
            projectId: this.projectId,
            kpis: {},
            chartData: {},
            recentActivities: [],
            error: null,
        });

        onWillStart(() => this.fetchProjectData());

        onMounted(() => {
            this._interval = setInterval(() => this.fetchProjectData(), 300000); // Refresh every 5 minutes
            this.renderCharts();
        });

        onWillUnmount(() => {
            if (this._interval) clearInterval(this._interval);
            this.destroyCharts();
        });
    }

    async fetchProjectData() {
        if (!this.projectId) {
            this.state.error = "No project selected";
            this.state.loading = false;
            return;
        }

        try {
            this.state.loading = true;
            const result = await this.orm.call(
                "construction.dashboard.service",
                "get_project_dashboard_data",
                [this.projectId],
                {}
            );

            if (result.error) {
                this.state.error = result.error;
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.state.kpis = result.kpis || {};
                this.state.chartData = result.chartData || {};
                this.state.recentActivities = result.recentActivities || [];
                this.state.error = null;
                setTimeout(() => this.renderCharts(), 100);
            }
        } catch (e) {
            console.error("Project Dashboard fetch failed", e);
            this.state.error = "Failed to load dashboard data";
            this.notification.add("Failed to load dashboard data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    destroyCharts() {
        const chartInstances = [
            'taskProgressChartInstance',
            'costBreakdownChartInstance',
            'monthlyProgressChartInstance',
            'materialConsumptionChartInstance',
            'laborUtilizationChartInstance',
            'timelineChartInstance',
            'costComparisonChartInstance'
        ];

        chartInstances.forEach(instance => {
            if (this[instance]) {
                this[instance].destroy();
                this[instance] = null;
            }
        });
    }

    renderCharts() {
        if (this.state.error || this.state.loading) return;

        this.renderTaskProgressChart();
        this.renderCostBreakdownChart();
        this.renderMonthlyProgressChart();
        this.renderMaterialConsumptionChart();
        this.renderLaborUtilizationChart();
        this.renderCostComparisonChart();
    }

    renderTaskProgressChart() {
        const canvas = document.getElementById('projectTaskProgressChart');
        if (!canvas || !this.state.chartData.taskProgress) return;

        const ctx = canvas.getContext('2d');
        const allTasks = this.state.chartData.taskProgress;

        // ✅ Only include main tasks (exclude subtasks)
        const tasks = allTasks.filter(item => !item.parentId);
        // adjust condition based on your data model
        // e.g., `item.isSubtask === false` or `item.level === 0`

        if (this.taskProgressChartInstance) {
            this.taskProgressChartInstance.destroy();
        }

        this.taskProgressChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: tasks.map(item => item.taskName),
                datasets: [{
                    label: 'Progress (%)',
                    data: tasks.map(item => item.progress),
                    backgroundColor: tasks.map(item => {
                        if (item.status === 'completed') return '#27ae60';
                        if (item.status === 'in_progress') return '#f39c12';
                        return '#95a5a6';
                    }),
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Task Progress' },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const task = tasks[context.dataIndex];
                                return [
                                    `Status: ${task.status}`,
                                    `Duration: ${task.duration} days`,
                                    `Assigned: ${task.assignedTo}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });
    }


    renderCostBreakdownChart() {
        const canvas = document.getElementById('projectCostBreakdownChart');
        if (!canvas || !this.state.chartData.costBreakdown) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.costBreakdown;

        if (this.costBreakdownChartInstance) {
            this.costBreakdownChartInstance.destroy();
        }

        this.costBreakdownChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(item => item.category),
                datasets: [{
                    data: data.map(item => item.amount),
                    backgroundColor: ['#e74c3c', '#f39c12', '#27ae60', '#2791ae'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Cost Breakdown' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const item = data[context.dataIndex];
                                return `${context.label}: ₹${item.amount.toLocaleString()} (${item.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderMonthlyProgressChart() {
        const canvas = document.getElementById('projectMonthlyProgressChart');
        if (!canvas || !this.state.chartData.monthlyProgress) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.monthlyProgress;

        if (this.monthlyProgressChartInstance) {
            this.monthlyProgressChartInstance.destroy();
        }

        this.monthlyProgressChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(item => item.month),
                datasets: [
                    {
                        label: 'Labor Hours',
                        data: data.map(item => item.laborHours),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Employee Count',
                        data: data.map(item => item.employeeCount),
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Monthly Progress Trends' }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Hours' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Employee Count' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    renderMaterialConsumptionChart() {
        const canvas = document.getElementById('projectMaterialConsumptionChart');
        if (!canvas || !this.state.chartData.materialConsumption) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.materialConsumption;

        if (this.materialConsumptionChartInstance) {
            this.materialConsumptionChartInstance.destroy();
        }

        this.materialConsumptionChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(item => item.material),
                datasets: [{
                    label: 'Total Cost',
                    data: data.map(item => item.totalPrice),
                    backgroundColor: '#9b59b6',
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Top Material Costs' },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const item = data[context.dataIndex];
                                return [
                                    `Quantity: ${item.requiredQuantity} ${item.unit}`,
                                    `Unit Price: ₹${item.unitPrice}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    renderLaborUtilizationChart() {
        const canvas = document.getElementById('projectLaborUtilizationChart');
        if (!canvas || !this.state.chartData.laborUtilization) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.laborUtilization;

        if (this.laborUtilizationChartInstance) {
            this.laborUtilizationChartInstance.destroy();
        }

        this.laborUtilizationChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(item => item.employee),
                datasets: [{
                    label: 'Total Hours',
                    data: data.map(item => item.totalHours),
                    backgroundColor: '#1abc9c',
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Employee Work Hours' },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const item = data[context.dataIndex];
                                return [
                                    `Work Days: ${item.workDays}`,
                                    `Avg Hours/Day: ${item.avgHoursPerDay}`
                                ];
                            }
                        }
                    }
                }
            }
        });
    }

    renderCostComparisonChart() {
        const canvas = document.getElementById('projectCostComparisonChart');
        if (!canvas || !this.state.chartData.costComparison) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.costComparison;

        if (this.costComparisonChartInstance) {
            this.costComparisonChartInstance.destroy();
        }

        this.costComparisonChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Material', 'Labor', 'Equipment', 'Total'],
                datasets: [
                    {
                        label: 'Expected Cost',
                        data: [
                            data.expected?.material || 0,
                            data.expected?.labor || 0,
                            data.expected?.equipment || 0,
                            data.expected?.total || 0
                        ],
                        backgroundColor: '#2ecc71',
                    },
                    {
                        label: 'Actual Cost',
                        data: [
                            data.actual?.material || 0,
                            data.actual?.labor || 0,
                            data.actual?.equipment || 0,
                            data.actual?.total || 0
                        ],
                        backgroundColor: '#e74c3c',
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Expected vs Actual Costs' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ₹${context.raw.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    backToProjects() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Construction Projects",
            res_model: "construction.project",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openProjectForm() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.state.kpis.projectName || "Project",
            res_model: "construction.project",
            res_id: this.projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    refreshDashboard() {
        this.fetchProjectData();
        this.notification.add("Dashboard refreshed", { type: "success" });
    }
}

ProjectDashboard.template = "construction.ProjectDashboard";
registry.category("actions").add("construction_project_dashboard.client_action", ProjectDashboard);