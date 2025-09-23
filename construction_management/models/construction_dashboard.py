from odoo import models, fields, api
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ConstructionDashboardService(models.AbstractModel):
    _name = "construction.dashboard.service"
    _description = "Construction Dashboard Service"

    def _safe_count(self, model, domain=None):
        """Safely count records with error handling"""
        try:
            if domain is None:
                domain = []
            return self.env[model].search_count(domain)
        except Exception as e:
            _logger.error(f"Error counting {model}: {e}")
            return 0

    def _safe_sum(self, records, field_name):
        """Safely sum field values with error handling"""
        try:
            return sum(records.mapped(field_name)) if records else 0
        except Exception as e:
            _logger.error(f"Error summing {field_name}: {e}")
            return 0

    @api.model
    def get_initial_kpis(self):
        """Legacy method for backward compatibility"""
        return self.get_dashboard_data()['kpis']

    @api.model
    def get_dashboard_data(self):
        """Get both KPIs and chart data for construction dashboard"""
        kpis = {
            "totalProjects": self._safe_count("construction.project"),
            # "totalinventory": self._safe_count("construction.inventory"),
            "employees": self._safe_count("construction.employee.work"),
            "totalProjectCosts": self._get_total_project_costs(),
            "actualProjectCosts": self._get_actual_project_costs(),
            "varianceCosts": self._get_project_cost_variance(),
            # "totalContractValue": self._get_total_contract_value(),
            # "totalProjectCosts": self._get_total_project_costs(),
            # # "profitMargin": self._get_profit_margin(),
            # "overallProgress": self._get_overall_progress(),
            # "activeEmployees": self._get_active_employees(),
            # "equipmentUtilization": self._get_equipment_utilization(),
            # "safetyIncidents": self._safe_count("construction.quality"),
            # "pendingInvoices": self._get_pending_invoices(),
            # "materialsOnSite": self._get_materials_on_site(),
        }

        chart_data = {
            "projectProgressChart": self._get_project_progress_chart(),
            "costBreakdown": self._get_cost_breakdown(),
            "equipmentAllocation": self._get_equipment_allocation_chart(),
            "laborProductivity": self._get_labor_productivity(),
            "materialConsumption": self._get_material_consumption(),
            "assetsEstimationChart": self._get_assets_summary(),
            "projectTimeline": self._get_project_timeline(),
            "costComparison": self._get_project_cost_comparison_chart(),
            "inventoryAllocationChart": self._get_inventory_allocation_chart(),
        }

        return {
            "kpis": kpis,
            "chartData": chart_data
        }

    def _get_total_contract_value(self):
        """Get total contract value of all projects"""
        try:
            projects = self.env['construction.project'].search([])
            total = self._safe_sum(projects, 'contract_value')
            return f"${total:,.2f}" if total else "$0.00"
        except Exception:
            return "$0.00"

    def _get_total_project_costs(self):
        """Get total costs across all projects"""
        try:
            projects = self.env['construction.project'].search([])
            total = self._safe_sum(projects, 'e_total_cost')
            return f"₹{total:,.2f}" if total else "$0.00"
        except Exception:
            return "$0.00"

    def _get_actual_project_costs(self):
        """Get total costs across all projects"""
        try:
            projects = self.env['construction.project'].search([])
            total = self._safe_sum(projects, 'total_cost')
            return f"₹{total:,.2f}" if total else "$0.00"
        except Exception:
            return "$0.00"

    def _get_project_cost_variance(self):
        """Calculate total cost variance across all projects"""
        try:
            projects = self.env['construction.project'].search([])
            total_estimated = self._safe_sum(projects, 'e_total_cost')  # Estimated cost
            total_actual = self._safe_sum(projects, 'total_cost')  # Actual cost
            variance_percentage = round(((total_actual - total_estimated) / total_estimated) * 100, 1)
            return f"₹{abs(variance_percentage):,.2f}%" if variance_percentage else "₹0.00"
        except Exception:
            return "₹0.00"

    def _get_overall_progress(self):
        """Get weighted average progress of all active projects"""
        try:
            active_projects = self.env['construction.project'].search([('state', '=', 'active')])
            if not active_projects:
                return "0%"

            total_weighted_progress = 0
            total_weight = 0

            for project in active_projects:
                weight = project.contract_value or 1
                progress = project.progress_percent or 0
                total_weighted_progress += progress * weight
                total_weight += weight

            if total_weight > 0:
                avg_progress = total_weighted_progress / total_weight
                return f"{avg_progress:.1f}%"
            return "0%"
        except Exception:
            return "0%"

    def _get_inventory_allocation_chart(self):
        """Get inventory allocation of materials across projects"""
        try:
            boq_items = self.env['construction.boq'].search([])

            project_allocations = {}
            for boq in boq_items:
                if boq.project_id and boq.material_id:
                    project_name = boq.project_id.name

                    # Get the inventory for this material
                    inventory = self.env['construction.inventory'].search([
                        ('material_id', '=', boq.material_id.id)
                    ], limit=1)

                    if inventory:
                        # Calculate allocation: min(required_qty, available_stock)
                        allocated = min(boq.quantity, inventory.current_stock)
                        project_allocations[project_name] = project_allocations.get(project_name, 0) + allocated

            labels = list(project_allocations.keys())
            data = list(project_allocations.values())

            # If no data, return demo values
            return {
                "labels": labels,
                "data": data,
            }
        except Exception as e:
            _logger.error(f"Error in _get_inventory_allocation_chart: {e}")
            return {
                "labels": ["Project A", "Project B"],
                "data": [100, 150],
            }

    def _get_project_progress_chart(self):
        """Get progress data for all active projects"""
        try:
            projects = self.env['construction.project'].search([])

            data = []
            for project in projects:
                data.append({
                    'projectName': project.name,
                    'progress': project.progress_percent or 0,
                    'contractValue': project.contract_value or 0,
                    'totalCost': project.total_cost or 0,
                    'status': project.state,
                    'startDate': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                    'endDate': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
                })

            # If no data, return sample data
            if not data:
                data = [
                    {'projectName': 'Office Building A', 'progress': 75, 'contractValue': 500000, 'totalCost': 450000,
                     'status': 'active'},
                    {'projectName': 'Residential Complex', 'progress': 45, 'contractValue': 750000, 'totalCost': 300000,
                     'status': 'active'},
                    {'projectName': 'Shopping Mall', 'progress': 90, 'contractValue': 1200000, 'totalCost': 1100000,
                     'status': 'active'},
                ]

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_progress_chart: {e}")
            return [
                {'projectName': 'Office Building A', 'progress': 75, 'contractValue': 500000, 'totalCost': 450000,
                 'status': 'active'},
                {'projectName': 'Residential Complex', 'progress': 45, 'contractValue': 750000, 'totalCost': 300000,
                 'status': 'active'},
            ]

    def _get_project_cost_comparison_chart(self):
        """Get contract value vs total cost for all projects"""
        try:
            projects = self.env['construction.project'].search([])

            data = []
            for project in projects:
                data.append({
                    'projectName': project.name,
                    'expectedValue': float(project.e_total_cost or 0),
                    'totalCost': float(project.total_cost or 0),
                    'status': project.state,
                })

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_cost_comparison_chart: {e}")
            return []

    def _get_cost_breakdown(self):
        """Get cost breakdown by category across all projects"""
        try:
            projects = self.env['construction.project'].search([])

            total_material = self._safe_sum(projects, 'material_cost')
            total_labor = self._safe_sum(projects, 'labor_cost')
            total_equipment = self._safe_sum(projects, 'equipment_cost')

            data = [
                {'category': 'Materials', 'amount': total_material, 'percentage': 0},
                {'category': 'Labor', 'amount': total_labor, 'percentage': 0},
                {'category': 'Equipment', 'amount': total_equipment, 'percentage': 0},
            ]

            total = total_material + total_labor + total_equipment
            if total > 0:
                for item in data:
                    item['percentage'] = round((item['amount'] / total) * 100, 1)

            # If no data, return sample data
            if total == 0:
                data = [
                    {'category': 'Materials', 'amount': 250000, 'percentage': 55.6},
                    {'category': 'Labor', 'amount': 150000, 'percentage': 33.3},
                    {'category': 'Equipment', 'amount': 50000, 'percentage': 11.1},
                ]

            return data
        except Exception as e:
            _logger.error(f"Error in _get_cost_breakdown: {e}")
            return [
                {'category': 'Materials', 'amount': 250000, 'percentage': 55.6},
                {'category': 'Labor', 'amount': 150000, 'percentage': 33.3},
                {'category': 'Equipment', 'amount': 50000, 'percentage': 11.1},
            ]

    def _get_monthly_progress(self):
        """Get monthly progress data for current year"""
        try:
            current_year = datetime.now().year
            monthly_data = {}

            # Get DPR records for the year to track monthly progress
            dpr_records = self.env['construction.dpr'].search([
                ('date', '>=', f'{current_year}-01-01'),
                ('date', '<', f'{current_year + 1}-01-01')
            ])

            for dpr in dpr_records:
                month_name = dpr.date.strftime('%B')
                if month_name not in monthly_data:
                    monthly_data[month_name] = {
                        'projects': set(),
                        'labor_hours': 0,
                        'employee_count': 0
                    }

                monthly_data[month_name]['projects'].add(dpr.project_id.id)
                monthly_data[month_name]['labor_hours'] += dpr.labor_hours or 0
                monthly_data[month_name]['employee_count'] += dpr.employee_count or 0

            # Convert to list format
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']

            data = []
            for month in month_names:
                if month in monthly_data:
                    data.append({
                        'month': month,
                        'activeProjects': len(monthly_data[month]['projects']),
                        'laborHours': monthly_data[month]['labor_hours'],
                        'employeeCount': monthly_data[month]['employee_count']
                    })
                else:
                    data.append({
                        'month': month,
                        'activeProjects': 0,
                        'laborHours': 0,
                        'employeeCount': 0
                    })

            # If no data, return sample data
            if not any(item['activeProjects'] for item in data):
                data = [
                    {'month': 'January', 'activeProjects': 3, 'laborHours': 520, 'employeeCount': 25},
                    {'month': 'February', 'activeProjects': 4, 'laborHours': 640, 'employeeCount': 32},
                    {'month': 'March', 'activeProjects': 5, 'laborHours': 720, 'employeeCount': 38},
                    {'month': 'April', 'activeProjects': 4, 'laborHours': 680, 'employeeCount': 35},
                    {'month': 'May', 'activeProjects': 5, 'laborHours': 750, 'employeeCount': 40},
                    {'month': 'June', 'activeProjects': 3, 'laborHours': 580, 'employeeCount': 28},
                ]

            return data
        except Exception as e:
            _logger.error(f"Error in _get_monthly_progress: {e}")
            return [
                {'month': 'January', 'activeProjects': 3, 'laborHours': 520, 'employeeCount': 25},
                {'month': 'February', 'activeProjects': 4, 'laborHours': 640, 'employeeCount': 32},
            ]

    def _get_equipment_allocation_chart(self):
        """Get equipment allocation status"""
        try:
            allocations = self.env['construction.equipment.allocation'].search([])

            status_data = {}
            for allocation in allocations:
                status = allocation.state
                if status not in status_data:
                    status_data[status] = 0
                status_data[status] += 1

            data = []
            for status, count in status_data.items():
                data.append({
                    'status': status.replace('_', ' ').title(),
                    'count': count
                })

            # If no data, return sample data
            if not data:
                data = [
                    {'status': 'In Use', 'count': 15},
                    {'status': 'Allocated', 'count': 8},
                    {'status': 'Available', 'count': 12},
                    {'status': 'Maintenance', 'count': 3},
                ]

            return data
        except Exception as e:
            _logger.error(f"Error in _get_equipment_allocation_chart: {e}")
            return [
                {'status': 'In Use', 'count': 15},
                {'status': 'Allocated', 'count': 8},
                {'status': 'Available', 'count': 12},
            ]

    def _get_labor_productivity(self):
        """Get labor productivity metrics"""
        try:
            current_month = datetime.now().replace(day=1)
            work_records = self.env['construction.employee.work'].search([
                ('work_date', '>=', current_month),
                ('state', 'in', ['confirmed', 'approved'])
            ])

            if not work_records:
                return [
                    {'project': 'Sample Project A', 'hoursWorked': 320, 'productivity': 85.5},
                    {'project': 'Sample Project B', 'hoursWorked': 280, 'productivity': 92.1},
                ]

            # Group by project
            project_data = {}
            for work in work_records:
                project_name = work.project_id.name
                if project_name not in project_data:
                    project_data[project_name] = {
                        'total_hours': 0,
                        'completed_tasks': 0
                    }

                project_data[project_name]['total_hours'] += work.working_hours or 0
                if hasattr(work, 'construction_task_id') and work.construction_task_id:
                    if hasattr(work.construction_task_id, 'status') and work.construction_task_id.status == 'completed':
                        project_data[project_name]['completed_tasks'] += 1

            data = []
            for project, stats in project_data.items():
                # Calculate productivity as completed tasks per hour * 100
                productivity = (stats['completed_tasks'] / stats['total_hours'] * 100) if stats[
                                                                                              'total_hours'] > 0 else 0
                data.append({
                    'project': project,
                    'hoursWorked': stats['total_hours'],
                    'productivity': round(productivity, 1)
                })

            return data[:10]  # Limit to top 10
        except Exception as e:
            _logger.error(f"Error in _get_labor_productivity: {e}")
            return [
                {'project': 'Sample Project A', 'hoursWorked': 320, 'productivity': 85.5},
                {'project': 'Sample Project B', 'hoursWorked': 280, 'productivity': 92.1},
            ]

    def _get_material_consumption(self):
        """Get material consumption trends"""
        try:
            current_month = datetime.now().replace(day=1)
            dpr_materials = self.env['construction.dpr.material'].search([
                ('dpr_id.date', '>=', current_month)
            ])

            material_data = {}
            for material in dpr_materials:
                product_name = material.product_id.name
                if product_name not in material_data:
                    material_data[product_name] = {
                        'quantity': 0,
                        'cost': 0
                    }

                material_data[product_name]['quantity'] += material.quantity or 0
                material_data[product_name]['cost'] += material.total_cost or 0

            data = []
            for material, stats in material_data.items():
                data.append({
                    'material': material,
                    'quantity': stats['quantity'],
                    'totalCost': stats['cost']
                })

            # Sort by cost descending and limit to top 10
            data.sort(key=lambda x: x['totalCost'], reverse=True)
            data = data[:10]

            # If no data, return sample data
            if not data:
                data = [
                    {'material': 'Cement', 'quantity': 500, 'totalCost': 25000},
                    {'material': 'Steel Bars', 'quantity': 200, 'totalCost': 15000},
                    {'material': 'Concrete Blocks', 'quantity': 1000, 'totalCost': 8000},
                    {'material': 'Sand', 'quantity': 50, 'totalCost': 3000},
                ]

            return data
        except Exception as e:
            _logger.error(f"Error in _get_material_consumption: {e}")
            return [
                {'material': 'Cement', 'quantity': 500, 'totalCost': 25000},
                {'material': 'Steel Bars', 'quantity': 200, 'totalCost': 15000},
            ]

    def _get_financial_summary(self):
        """Get financial summary data"""
        try:
            projects = self.env['construction.project'].search([])

            total_contract = self._safe_sum(projects, 'contract_value')
            total_invoiced = self._safe_sum(projects, 'total_invoiced')
            total_paid = self._safe_sum(projects, 'total_paid')
            total_costs = self._safe_sum(projects, 'total_cost')

            data = {
                'totalContract': total_contract,
                'totalInvoiced': total_invoiced,
                'totalReceived': total_paid,
                'totalCosts': total_costs,
                'outstandingAmount': total_invoiced - total_paid,
                'profitLoss': total_paid - total_costs,
                'invoicingProgress': (total_invoiced / total_contract * 100) if total_contract > 0 else 0,
                'collectionProgress': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0,
            }

            # If no data, return sample data
            if total_contract == 0:
                data = {
                    'totalContract': 1500000,
                    'totalInvoiced': 900000,
                    'totalReceived': 750000,
                    'totalCosts': 650000,
                    'outstandingAmount': 150000,
                    'profitLoss': 100000,
                    'invoicingProgress': 60.0,
                    'collectionProgress': 83.3,
                }

            return data
        except Exception as e:
            _logger.error(f"Error in _get_financial_summary: {e}")
            return {
                'totalContract': 1500000,
                'totalInvoiced': 900000,
                'totalReceived': 750000,
                'totalCosts': 650000,
                'outstandingAmount': 150000,
                'profitLoss': 100000,
                'invoicingProgress': 60.0,
                'collectionProgress': 83.3,
            }

    def _get_assets_summary(self):
        """Get actual vs expected asset estimation costs"""
        try:
            projects = self.env['construction.project'].search([])

            actual = {
                'material': sum(projects.mapped('material_cost')),
                'labor': sum(projects.mapped('labor_cost')),
                'equipment': sum(projects.mapped('equipment_cost')),
                'total': sum(projects.mapped('total_cost')),
            }
            expected = {
                'material': sum(projects.mapped('e_material_cost')),
                'labor': sum(projects.mapped('e_labor_cost')),
                'equipment': sum(projects.mapped('e_equipment_cost')),
                'total': sum(projects.mapped('e_total_cost')),
            }

            return {
                'actual': actual,
                'expected': expected
            }
        except Exception as e:
            _logger.error(f"Error in _get_assets_summary: {e}")
            return {
                'actual': {'material': 0, 'labor': 0, 'equipment': 0, 'total': 0},
                'expected': {'material': 0, 'labor': 0, 'equipment': 0, 'total': 0},
            }

    def _get_project_timeline(self):
        """Get upcoming project milestones and deadlines"""
        try:
            today = date.today()
            upcoming_date = today + timedelta(days=30)

            tasks = self.env['project.task.simple'].search([
                ('end_date', '>=', today),
                ('end_date', '<=', upcoming_date),
                ('status', '!=', 'completed')
            ])

            data = []
            for task in tasks:
                days_remaining = (task.end_date - today).days
                data.append({
                    'taskName': task.name,
                    'projectName': task.project_id.name,
                    'endDate': task.end_date.strftime('%Y-%m-%d'),
                    'daysRemaining': days_remaining,
                    'progress': task.progress_percent or 0,
                    'status': task.status,
                    'isOverdue': task.end_date < today
                })

            # Sort by end date
            data.sort(key=lambda x: x['endDate'])

            # If no data, return sample data
            if not data:
                data = [
                    {'taskName': 'Foundation Work', 'projectName': 'Office Building', 'endDate': '2024-12-15',
                     'daysRemaining': 5, 'progress': 80, 'status': 'in_progress', 'isOverdue': False},
                    {'taskName': 'Electrical Installation', 'projectName': 'Residential Complex',
                     'endDate': '2024-12-20', 'daysRemaining': 10, 'progress': 45, 'status': 'in_progress',
                     'isOverdue': False},
                ]

            return data[:10]  # Limit to next 10 tasks
        except Exception as e:
            _logger.error(f"Error in _get_project_timeline: {e}")
            return [
                {'taskName': 'Foundation Work', 'projectName': 'Office Building', 'endDate': '2024-12-15',
                 'daysRemaining': 5, 'progress': 80, 'status': 'in_progress', 'isOverdue': False},
            ]

    #Individual Dashboard
    @api.model
    def get_project_dashboard_data(self, project_id):
        """Get comprehensive dashboard data for a specific project"""
        try:
            project = self.env['construction.project'].browse(project_id)
            if not project.exists():
                return {'error': 'Project not found'}

            # Project KPIs
            kpis = {
                'projectName': project.name,
                'contractValue': project.contract_value or 0,
                'totalCost': project.total_cost or 0,
                'etotalCost': project.e_total_cost or 0,
                'materialCost': project.material_cost or 0,
                'laborCost': project.labor_cost or 0,
                'equipmentCost': project.equipment_cost or 0,
                'progress': project.progress_percent or 0,
                'status': project.state,
                'totalTasks': len(project.timeline_ids),
                'completedTasks': len(project.timeline_ids.filtered(lambda t: t.status == 'completed')),
                'activeTasks': len(project.timeline_ids.filtered(lambda t: t.status == 'in_progress')),
                'totalBOQItems': len(project.boq_ids),
                'totalDPRs': len(project.dpr_ids),
                'totalQualityRecords': len(project.quality_ids),
                'startDate': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                'endDate': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
                'expectedStartDate': project.e_start_date.strftime('%Y-%m-%d') if project.e_start_date else None,
                'expectedEndDate': project.e_end_date.strftime('%Y-%m-%d') if project.e_end_date else None,
            }

            # Calculate additional metrics
            if kpis['totalTasks'] > 0:
                kpis['taskCompletionRate'] = round((kpis['completedTasks'] / kpis['totalTasks']) * 100, 1)
            else:
                kpis['taskCompletionRate'] = 0

            # Cost variance
            expected_total = (project.e_material_cost or 0) + (project.e_labor_cost or 0) + (project.e_equipment_cost or 0) + (project.e_contract_value or 0)
            if expected_total > 0:
                variance = round(((expected_total - kpis['totalCost']) / expected_total) * 100, 1)
                kpis['costVariance'] = variance
                if variance > 0:
                    kpis['costVarianceMsg'] = f"{variance}% higher than the expected total cost"
                elif variance < 0:
                    kpis['costVarianceMsg'] = f"{abs(variance)}% lower than the expected total cost"
                else:
                    kpis['costVarianceMsg'] = "On target with expected total cost"
            else:
                kpis['costVariance'] = 0
                kpis['costVarianceMsg'] = "No expected cost available"

            # Chart data
            chart_data = {
                'taskProgress': self._get_project_task_progress(project),
                'costBreakdown': self._get_project_cost_breakdown(project),
                'monthlyProgress': self._get_project_monthly_progress(project),
                'materialConsumption': self._get_project_material_consumption(project),
                'laborUtilization': self._get_project_labor_utilization(project),
                'timeline': self._get_project_timeline_chart(project),
                'boqProgress': self._get_project_boq_progress(project),
                'costComparison': self._get_project_cost_comparison(project),
            }

            return {
                'kpis': kpis,
                'chartData': chart_data,
                'recentActivities': self._get_project_recent_activities(project),
            }

        except Exception as e:
            _logger.error(f"Error in get_project_dashboard_data: {e}")
            return {'error': str(e)}

    def _get_project_task_progress(self, project):
        """Get task progress for the project (including subtasks)"""
        try:
            tasks = self.env['project.task.simple'].search([('project_id', '=', project.id)])
            data = []
            for task in tasks:
                data.append({
                    'taskName': task.display_name,  # shows indentation for hierarchy
                    'progress': task.progress_percent or 0,
                    'status': task.status,
                    'startDate': task.start_date.strftime('%Y-%m-%d') if task.start_date else None,
                    'endDate': task.end_date.strftime('%Y-%m-%d') if task.end_date else None,
                    'duration': task.duration or 0,
                    'assignedTo': task.assigned_to.name if task.assigned_to else 'Unassigned',
                    'isSubtask': task.is_subtask,
                    'parent': task.parent_id.display_name if task.parent_id else None,
                })
            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_task_progress: {e}")
            return []

    def _get_project_cost_breakdown(self, project):
        """Get cost breakdown for the project"""
        try:
            total = project.total_cost or 0
            if total == 0:
                return []

            data = [
                {
                    'category': 'Materials',
                    'amount': project.material_cost or 0,
                    'percentage': round(((project.material_cost or 0) / total) * 100, 1)
                },
                {
                    'category': 'Labor',
                    'amount': project.labor_cost or 0,
                    'percentage': round(((project.labor_cost or 0) / total) * 100, 1)
                },
                {
                    'category': 'Equipment',
                    'amount': project.equipment_cost or 0,
                    'percentage': round(((project.equipment_cost or 0) / total) * 100, 1)
                },
                {
                    'category': 'Contract',
                    'amount': project.contract_value or 0,
                    'percentage': round(((project.contract_value or 0) / total) * 100, 1)
                }
            ]
            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_cost_breakdown: {e}")
            return []

    def _get_project_monthly_progress(self, project):
        """Get monthly progress for the project"""
        try:
            current_year = datetime.now().year
            dpr_records = project.dpr_ids.filtered(
                lambda d: d.date and d.date.year == current_year
            )

            monthly_data = {}
            for dpr in dpr_records:
                month_name = dpr.date.strftime('%B')
                if month_name not in monthly_data:
                    monthly_data[month_name] = {
                        'laborHours': 0,
                        'employeeCount': 0,
                        'dprCount': 0
                    }

                monthly_data[month_name]['laborHours'] += dpr.labor_hours or 0
                monthly_data[month_name]['employeeCount'] += dpr.employee_count or 0
                monthly_data[month_name]['dprCount'] += 1

            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']

            data = []
            for month in month_names:
                if month in monthly_data:
                    data.append({
                        'month': month,
                        'laborHours': monthly_data[month]['laborHours'],
                        'employeeCount': monthly_data[month]['employeeCount'],
                        'dprCount': monthly_data[month]['dprCount']
                    })
                else:
                    data.append({
                        'month': month,
                        'laborHours': 0,
                        'employeeCount': 0,
                        'dprCount': 0
                    })

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_monthly_progress: {e}")
            return []

    def _get_project_material_consumption(self, project):
        """Get material consumption for the project"""
        try:
            boq_items = project.boq_ids
            data = []

            for boq in boq_items:
                if boq.material_id:
                    data.append({
                        'material': boq.material_id.name,
                        'requiredQuantity': boq.quantity or 0,
                        'unitPrice': boq.unit_price or 0,
                        'totalPrice': boq.total_price or 0,
                        'unit': boq.unit or 'Unit'
                    })

            # Sort by total price descending
            data.sort(key=lambda x: x['totalPrice'], reverse=True)
            return data[:10]  # Top 10 materials
        except Exception as e:
            _logger.error(f"Error in _get_project_material_consumption: {e}")
            return []

    def _get_project_labor_utilization(self, project):
        """Get labor utilization for the project"""
        try:
            # Get employee work records for this project
            work_records = self.env['construction.employee.work'].search([
                ('project_id', '=', project.id),
                ('state', 'in', ['confirmed', 'approved'])
            ])

            employee_data = {}
            for work in work_records:
                emp_name = work.employee_id.name if work.employee_id else 'Unknown'
                if emp_name not in employee_data:
                    employee_data[emp_name] = {
                        'totalHours': 0,
                        'workDays': 0
                    }

                employee_data[emp_name]['totalHours'] += work.working_hours or 0
                employee_data[emp_name]['workDays'] += 1

            data = []
            for emp_name, stats in employee_data.items():
                data.append({
                    'employee': emp_name,
                    'totalHours': stats['totalHours'],
                    'workDays': stats['workDays'],
                    'avgHoursPerDay': round(stats['totalHours'] / stats['workDays'], 1) if stats['workDays'] > 0 else 0
                })

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_labor_utilization: {e}")
            return []

    def _get_project_timeline_chart(self, project):
        """Get timeline chart data for the project"""
        try:
            tasks = project.timeline_ids.sorted('start_date')
            data = []

            for task in tasks:
                data.append({
                    'taskName': task.name,
                    'startDate': task.start_date.strftime('%Y-%m-%d') if task.start_date else None,
                    'endDate': task.end_date.strftime('%Y-%m-%d') if task.end_date else None,
                    'progress': task.progress_percent or 0,
                    'status': task.status,
                    'duration': task.duration or 0
                })

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_timeline_chart: {e}")
            return []

    def _get_project_boq_progress(self, project):
        """Get BOQ progress for the project"""
        try:
            boq_items = project.boq_ids
            total_items = len(boq_items)
            completed_items = len(boq_items.filtered(lambda b: getattr(b, 'status', 'pending') == 'completed'))

            data = {
                'totalItems': total_items,
                'completedItems': completed_items,
                'pendingItems': total_items - completed_items,
                'completionRate': round((completed_items / total_items) * 100, 1) if total_items > 0 else 0
            }

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_boq_progress: {e}")
            return {'totalItems': 0, 'completedItems': 0, 'pendingItems': 0, 'completionRate': 0}

    def _get_project_cost_comparison(self, project):
        """Get cost comparison between expected and actual"""
        try:
            data = {
                'expected': {
                    'material': project.e_material_cost or 0,
                    'labor': project.e_labor_cost or 0,
                    'equipment': project.e_equipment_cost or 0,
                    'contract': project.e_contract_value or 0,
                    'total': project.e_total_cost or 0
                },
                'actual': {
                    'material': project.material_cost or 0,
                    'labor': project.labor_cost or 0,
                    'equipment': project.equipment_cost or 0,
                    'contract': project.contract_value or 0,
                    'total': project.total_cost or 0
                }
            }

            return data
        except Exception as e:
            _logger.error(f"Error in _get_project_cost_comparison: {e}")
            return {}

    def _get_project_recent_activities(self, project):
        """Get recent activities for the project"""
        try:
            activities = []

            # Recent DPRs
            recent_dprs = project.dpr_ids.sorted('date', reverse=True)[:5]
            for dpr in recent_dprs:
                activities.append({
                    'type': 'DPR',
                    'title': f'Daily Progress Report - {dpr.date.strftime("%Y-%m-%d")}',
                    'date': dpr.date.strftime('%Y-%m-%d'),
                    'description': dpr.summary or 'Daily progress updated'
                })

            # Recent quality records
            recent_quality = project.quality_ids.sorted('create_date', reverse=True)[:3]
            for quality in recent_quality:
                activities.append({
                    'type': 'Quality',
                    'title': f'Quality Check - {quality.name}',
                    'date': quality.create_date.strftime('%Y-%m-%d') if quality.create_date else '',
                    'description': 'Quality inspection completed'
                })

            # Sort by date descending
            activities.sort(key=lambda x: x['date'], reverse=True)
            return activities[:10]  # Return top 10 recent activities

        except Exception as e:
            _logger.error(f"Error in _get_project_recent_activities: {e}")
            return []