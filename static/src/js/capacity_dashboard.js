/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class KioCapacityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            summary: {
                totalActiveCapacity: 0,
                totalSpend: 0,
                totalCapacityItems: 0,
            },
            capacityItems: [],
            dateFrom: "",
            dateTo: "",
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;

        try {
            const purchaseDomain = [];
            if (this.state.dateFrom) {
                purchaseDomain.push(["purchase_date", ">=", this.state.dateFrom]);
            }
            if (this.state.dateTo) {
                purchaseDomain.push(["purchase_date", "<=", this.state.dateTo]);
            }

            const serviceProducts = await this.orm.searchRead(
                "product.template",
                [
                    ["detailed_type", "=", "service"],
                    ["is_upstream_service", "=", true],
                ],
                ["id", "name", "active", "is_upstream_service"],
                { context: { active_test: false } }
            );

            const purchases = await this.orm.searchRead(
                "kio.capacity.upstream.purchase",
                purchaseDomain,
                ["id", "active"],
                { context: { active_test: false } }
            );

            const purchaseIds = purchases.map((p) => p.id);
            const purchaseLineDomain = purchaseIds.length
                ? [["purchase_id", "in", purchaseIds]]
                : [["id", "=", 0]];

            const purchaseLines = await this.orm.searchRead(
                "kio.capacity.upstream.purchase.line",
                purchaseLineDomain,
                [
                    "capacity_item_id",
                    "purchased_capacity",
                    "total_price",
                    "purchase_id",
                ],
                { context: { active_test: false } }
            );

            const activePurchaseIds = new Set(
                purchases.filter((p) => p.active).map((p) => p.id)
            );

            const itemMap = new Map();
            let totalActiveCapacity = 0;
            let totalSpend = 0;

            for (const product of serviceProducts) {
                itemMap.set(product.id, {
                    itemId: product.id,
                    itemName: product.name,
                    active: product.active,
                    totalCapacity: 0,
                    totalPrice: 0,
                    purchaseCount: 0,
                });
            }

            for (const line of purchaseLines) {
                const capacityItemName = line.capacity_item_id
                    ? line.capacity_item_id[1]
                    : null;

                for (const item of itemMap.values()) {
                    if (capacityItemName && capacityItemName === item.itemName) {
                        const capacity = line.purchased_capacity || 0;
                        const price = line.total_price || 0;

                        item.totalCapacity += capacity;
                        item.totalPrice += price;
                        item.purchaseCount += 1;

                        if (
                            line.purchase_id &&
                            activePurchaseIds.has(line.purchase_id[0])
                        ) {
                            totalActiveCapacity += capacity;
                        }

                        totalSpend += price;
                        break;
                    }
                }
            }

            this.state.summary = {
                totalActiveCapacity,
                totalSpend,
                totalCapacityItems: serviceProducts.length,
            };

            this.state.capacityItems = Array.from(itemMap.values()).sort((a, b) =>
                a.itemName.localeCompare(b.itemName)
            );
        } catch (error) {
            console.error("Dashboard Load Error:", error);
            this.state.capacityItems = [];
        } finally {
            this.state.loading = false;
        }
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    async onDateRangeChange(field, value) {
        this.state[field] = value;
        await this.loadDashboardData();
    }

    async clearDateRange() {
        this.state.dateFrom = "";
        this.state.dateTo = "";
        await this.loadDashboardData();
    }

    getPurchaseDomain(item) {
        const domain = [["line_ids.capacity_item_id.name", "=", item.itemName]];
        if (this.state.dateFrom) {
            domain.push(["purchase_date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["purchase_date", "<=", this.state.dateTo]);
        }
        return domain;
    }

    openCapacityItemPurchases(item) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${item.itemName} - Purchases`,
            res_model: "kio.capacity.upstream.purchase",
            views: [
                [false, "tree"],
                [false, "form"],
            ],
            domain: this.getPurchaseDomain(item),
            context: { active_test: false },
            target: "current",
        });
    }

    openCapacityItemForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Create Upstream Service Product",
            res_model: "product.template",
            views: [[false, "form"]],
            context: {
                default_detailed_type: "service",
                default_is_upstream_service: true,
            },
            target: "current",
        });
    }
}

KioCapacityDashboard.template = "kio_capacity_analysis.CapacityDashboard";

registry
    .category("actions")
    .add("kio_capacity_analysis.capacity_dashboard", KioCapacityDashboard);