/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";

class ConstructionDashboard extends Component {
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
        this.state = useState({
            loading: true,
            kpis: {
                totalProjects: 0,
                totalinventory: 0,
                employees: 0,
//                activeProjects: 0,
//                completedProjects: 0,
//                totalContractValue: "$0.00",
//                totalProjectCosts: "$0.00",
//                profitMargin: "0%",
//                overallProgress: "0%",
//                activeEmployees: 0,
//                equipmentUtilization: "0%",
//                safetyIncidents: 0,
//                pendingInvoices: 0,
//                materialsOnSite: "$0.00",
            },
            chartData: {},
        });

        onWillStart(() => this.fetchKPIs());

        onMounted(() => {
            this._interval = setInterval(() => this.fetchKPIs(), 60000);
            this.renderCharts();
        });

        onWillUnmount(() => {
            if (this._interval) clearInterval(this._interval);
            if (this.projectProgressChartInstance) this.projectProgressChartInstance.destroy();
            if (this.costBreakdownChartInstance) this.costBreakdownChartInstance.destroy();
            if (this.monthlyProgressChartInstance) this.monthlyProgressChartInstance.destroy();
            if (this.equipmentAllocationChartInstance) this.equipmentAllocationChartInstance.destroy();
            if (this.costComparisonInstance) this.costComparisonInstance.destroy();
            if (this.InventoryAllocationChartInstance) this.InventoryAllocationChartInstance.destroy();
        });
    }

    async fetchKPIs() {
        try {
            this.state.loading = true;
            const result = await this.orm.call(
                "construction.dashboard.service",
                "get_dashboard_data",
                [],
                {}
            );
            this.state.kpis = Object.assign(this.state.kpis, result.kpis || {});
            this.state.chartData = result.chartData || {};
            setTimeout(() => this.renderCharts(), 100);
        } catch (e) {
            console.warn("Construction Dashboard fetch failed", e);
        } finally {
            this.state.loading = false;
        }
    }

    openModel = (model) => {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: model,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    renderCharts = () => {
        this.renderProjectProgressChart();
        this.renderCostBreakdownChart();
        this.renderMonthlyProgressChart();
        this.renderEquipmentAllocationChart();
        this.rendercostComparison();
        this.renderInventoryAllocationChart()
    }

    renderProjectProgressChart = () => {
        const canvas = document.getElementById('projectProgressChart');
        if (!canvas || !this.state.chartData.projectProgressChart) return;
        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.projectProgressChart;

        if (this.projectProgressChartInstance) {
            this.projectProgressChartInstance.destroy();
        }

        this.projectProgressChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(item => item.projectName),
                datasets: [{
                    label: 'Progress (%)',
                    data: data.map(item => item.progress),
                    backgroundColor: '#3498db',
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Project Progress' }
                },
                scales: { y: { beginAtZero: true, max: 100 } }
            }
        });
    }

    renderCostBreakdownChart = () => {
        const canvas = document.getElementById('costBreakdownChart');
        if (!canvas || !this.state.chartData.costBreakdown) return;
        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.costBreakdown;

        if (this.costBreakdownChartInstance) {
            this.costBreakdownChartInstance.destroy();
        }

        this.costBreakdownChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.map(item => item.category),
                datasets: [{
                    data: data.map(item => item.amount),
                    backgroundColor: ['#e74c3c', '#f39c12', '#27ae60'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Cost Breakdown' }
                }
            }
        });
    }

    renderMonthlyProgressChart = () => {
        const canvas = document.getElementById('monthlyProgressChart');
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
                datasets: [{
                    label: 'Projects',
                    data: data.map(item => item.activeProjects),
                    borderColor: '#2980b9',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Monthly Progress' }
                }
            }
        });
    }

    renderEquipmentAllocationChart = () => {
        const canvas = document.getElementById('equipmentAllocationChart');
        if (!canvas || !this.state.chartData.equipmentAllocation) return;
        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.equipmentAllocation;

        if (this.equipmentAllocationChartInstance) {
            this.equipmentAllocationChartInstance.destroy();
        }

        this.equipmentAllocationChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(item => item.status),
                datasets: [{
                    data: data.map(item => item.count),
                    backgroundColor: ['#2ecc71', '#e67e22', '#95a5a6', '#9b59b6'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Equipment Allocation' }
                }
            }
        });
    }

    rendercostComparison = () => {
        const canvas = document.getElementById('costComparison');
        if (!canvas || !this.state.chartData.costComparison) return;
        const ctx = canvas.getContext('2d');
        const data = this.state.chartData.costComparison;

        console.log("Project Cost Comparison Data:", data);

        if (this.costComparisonInstance) {
            this.costComparisonInstance.destroy();
        }

        this.costComparisonInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(item => item.projectName),
                datasets: [
                    {
                        label: 'Expected Cost',
                        data: data.map(item => Number(item.expectedValue)),
                        backgroundColor: '#2ecc71',
                    },
                    {
                        label: 'Total Cost',
                        data: data.map(item => Number(item.totalCost)),
                        backgroundColor: '#e74c3c',
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Total Cost' },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.dataset.label + ": $" + context.raw.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return "$" + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    };

    renderInventoryAllocationChart = () => {
        const canvas = document.getElementById('inventoryAllocationChart');
        if (!canvas || !this.state.chartData.inventoryAllocationChart) return;
        const ctx = canvas.getContext('2d');
        const chartData = this.state.chartData.inventoryAllocationChart;

        if (this.inventoryAllocationChartInstance) {
            this.inventoryAllocationChartInstance.destroy();
        }

        this.inventoryAllocationChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Allocated Inventory',
                    data: chartData.data,
                    backgroundColor: ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#e74c3c'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Inventory Allocation by Project' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ": " + context.raw.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    };


}

ConstructionDashboard.template = "construction.ConstructionDashboard";
registry.category("actions").add("construction_dashboard.client_action", ConstructionDashboard);
