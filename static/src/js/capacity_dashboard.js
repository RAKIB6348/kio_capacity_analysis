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
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const capacityItems = await this.orm.searchRead(
            "kio.capacity.item",
            [],
            ["name", "active", "sequence"],
            { context: { active_test: false } }
        );
        const purchaseLines = await this.orm.searchRead(
            "kio.capacity.upstream.purchase.line",
            [],
            [
                "capacity_item_id",
                "purchased_capacity",
                "price",
                "total_price",
                "purchase_id",
            ],
            { context: { active_test: false } }
        );
        const purchases = await this.orm.searchRead(
            "kio.capacity.upstream.purchase",
            [],
            ["active"],
            { context: { active_test: false } }
        );
        const activePurchaseIds = new Set(
            purchases.filter((purchase) => purchase.active).map((purchase) => purchase.id)
        );

        const itemMap = new Map();
        let totalActiveCapacity = 0;
        let totalSpend = 0;

        for (const item of capacityItems) {
            itemMap.set(item.id, {
                itemId: item.id,
                itemName: item.name,
                active: item.active,
                sequence: item.sequence || 10,
                totalCapacity: 0,
                totalPrice: 0,
                purchaseCount: 0,
            });
        }

        for (const line of purchaseLines) {
            const itemId = line.capacity_item_id ? line.capacity_item_id[0] : false;
            const itemName = line.capacity_item_id ? line.capacity_item_id[1] : "No Capacity Item";
            const mapKey = itemId || "no_item";
            const capacity = line.purchased_capacity || 0;
            const totalPrice = line.total_price || 0;

            if (!itemMap.has(mapKey)) {
                itemMap.set(mapKey, {
                    itemId,
                    itemName,
                    active: false,
                    sequence: 9999,
                    totalCapacity: 0,
                    totalPrice: 0,
                    purchaseCount: 0,
                });
            }

            const item = itemMap.get(mapKey);
            item.totalCapacity += capacity;
            item.totalPrice += totalPrice;
            item.purchaseCount += 1;

            if (line.purchase_id && activePurchaseIds.has(line.purchase_id[0])) {
                totalActiveCapacity += capacity;
            }

            totalSpend += totalPrice;
        }

        this.state.summary = {
            totalActiveCapacity,
            totalSpend,
            totalCapacityItems: itemMap.size,
        };
        this.state.capacityItems = Array.from(itemMap.values()).sort((a, b) =>
            (a.sequence - b.sequence) || a.itemName.localeCompare(b.itemName)
        );
        this.state.loading = false;
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    openCapacityItemPurchases(item) {
        const domain = item.itemId
            ? [["line_ids.capacity_item_id", "=", item.itemId]]
            : [["line_ids.capacity_item_id", "=", false]];

        this.action.doAction({
            type: "ir.actions.act_window",
            name: item.itemName,
            res_model: "kio.capacity.upstream.purchase",
            views: [[false, "tree"], [false, "form"]],
            view_mode: "tree,form",
            domain,
            context: { active_test: false },
            target: "current",
        });
    }

    openCapacityItemForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Capacity Item",
            res_model: "kio.capacity.item",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
            context: { active_test: false },
        });
    }

}

KioCapacityDashboard.template = "kio_capacity_analysis.CapacityDashboard";

registry.category("actions").add("kio_capacity_analysis.capacity_dashboard", KioCapacityDashboard);
