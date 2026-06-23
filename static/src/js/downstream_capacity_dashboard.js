/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DownstreamCapacityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const currentMonthRange = this.getCurrentMonthRange();

        this.state = useState({
            loading: true,
            detailLoading: false,
            dateFrom: currentMonthRange.dateFrom,
            dateTo: currentMonthRange.dateTo,
            summary: {
                totalActiveCustomers: 0,
                totalAllocatedCapacity: 0,
                totalPackages: 0,
                totalMonthlyRevenue: 0,
            },
            packages: [],
            selectedPackage: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    getCurrentMonthRange() {
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        };

        return {
            dateFrom: formatDate(new Date(today.getFullYear(), today.getMonth(), 1)),
            dateTo: formatDate(new Date(today.getFullYear(), today.getMonth() + 1, 0)),
        };
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    getInitials(name) {
        return (name || "?").trim().slice(0, 1).toUpperCase();
    }

    async loadDashboardData() {
        this.state.loading = true;

        try {
            const data = await this.orm.call(
                "kio.capacity.dashboard",
                "get_downstream_capacity_dashboard_data",
                [],
                {
                    date_from: this.state.dateFrom || false,
                    date_to: this.state.dateTo || false,
                }
            );

            this.state.summary = data.summary || this.state.summary;
            this.state.packages = data.packages || [];

            if (this.state.selectedPackage) {
                const selectedPackage = this.state.packages.find(
                    (row) => row.packageId === this.state.selectedPackage.packageId
                );
                this.state.selectedPackage = selectedPackage || null;
            }
        } catch (error) {
            console.error("Downstream Capacity Dashboard Load Error:", error);
            this.state.packages = [];
        } finally {
            this.state.loading = false;
        }
    }

    async onDateRangeChange(field, value) {
        this.state[field] = value;
        await this.loadDashboardData();
    }

    async clearDateRange() {
        const currentMonthRange = this.getCurrentMonthRange();
        this.state.dateFrom = currentMonthRange.dateFrom;
        this.state.dateTo = currentMonthRange.dateTo;
        await this.loadDashboardData();
    }

    openPackage(packageRow) {
        this.state.selectedPackage = packageRow;
    }

    backToDashboard() {
        this.state.selectedPackage = null;
    }

    backToOverview() {
        this.action.doAction("kio_capacity_analysis.action_kio_capacity_dashboard");
    }

    openCustomerDetails(customer) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: customer.name,
            res_model: "isp.client",
            res_id: customer.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

DownstreamCapacityDashboard.template = "kio_capacity_analysis.DownstreamCapacityDashboard";

registry
    .category("actions")
    .add("kio_capacity_analysis.downstream_capacity_dashboard", DownstreamCapacityDashboard);
